"""Rechnen 算: generierte Rechenaufgaben wie in der AP1. ↵ prüft sofort, der Rechenweg erklärt, ↵ holt die nächste."""

import random
import time

from flask import Blueprint, abort, make_response, redirect, render_template, request, url_for

from saku.lernen import rechnen
from saku.web import db, ist_fragment, seite_oder_fragment

bp = Blueprint("rechnen", __name__, url_prefix="/rechnen")

SEEDS = 10 ** 6


def _stand(con) -> dict[str, dict]:
    """Je Art: wie viele Aufgaben gerechnet und die letzten zehn Ergebnisse (älteste zuerst, 1 = richtig)."""
    stand = {a: {"anzahl": 0, "letzte": []} for a in rechnen.ARTEN}
    for art, anzahl in con.execute("SELECT art, COUNT(*) FROM rechenuebung GROUP BY art"):
        if art in stand:
            stand[art]["anzahl"] = anzahl
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


def _art_oder_404(art: str) -> rechnen.Art:
    if art not in rechnen.ARTEN:
        abort(404)
    return rechnen.ARTEN[art]


def _kontext(art: str, seed: int, gemischt: bool, eingaben: dict | None = None, werte: dict | None = None,
             aufgegeben: bool = False) -> dict:
    naechste = url_for("rechnen.gemischt") if gemischt else url_for("rechnen.aufgabe", art=art, seed=random.randrange(SEEDS))
    return {"art": rechnen.ARTEN[art], "aufgabe": rechnen.erzeugen(art, seed), "seed": seed, "gemischt": gemischt,
            "start": int(time.time()), "eingaben": eingaben or {}, "werte": werte, "aufgegeben": aufgegeben,
            "naechste": naechste, "stand": _stand(db())[art]}


@bp.get("/")
def index():
    con = db()
    gruppen = [(g, [a for a in rechnen.ARTEN.values() if a.gruppe == g]) for g in rechnen.GRUPPEN]
    return render_template("rechnen/index.html", gruppen=gruppen, stand=_stand(con), heute=heute_gerechnet(con))


@bp.get("/gemischt")
def gemischt():
    """Eine Art nach Gewicht: was zuletzt oft falsch war (oder nie dran), kommt häufiger."""
    quoten = {a: sum(s["letzte"]) / len(s["letzte"]) for a, s in _stand(db()).items() if s["letzte"]}
    art = rechnen.gemischt(random.Random(), quoten)
    return redirect(url_for("rechnen.aufgabe", art=art, seed=random.randrange(SEEDS), gemischt=1))


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
    eingaben = {f.name: request.form.get(f"feld-{f.name}", "")[:200] for f in aufgabe.felder}
    aufgegeben = request.form.get("aufgeben") == "1"
    gemischt = request.form.get("gemischt") == "1"
    start = request.form.get("start", type=int)
    if not aufgegeben and not any(e.strip() for e in eingaben.values()):  # ↵ zu früh oder doppelt: nichts speichern
        return render_template("rechnen/_karte.html", **_kontext(art, seed, gemischt) | {"start": start or int(time.time()), "leer": True})
    werte = rechnen.pruefen(aufgabe, eingaben)
    dauer = min(max(int(time.time()) - start, 0), 3600) if start else None
    con = db()
    con.execute("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt, dauer_s) VALUES (?, ?, ?, ?, ?, ?)",
                (art, seed, int(not aufgegeben and all(werte.values())), sum(werte.values()), len(werte), dauer))
    con.commit()
    return render_template("rechnen/_karte.html", **_kontext(art, seed, gemischt, eingaben, werte, aufgegeben))
