"""Michi 道: der Lernpfad aus Trittsteinen. Station mit Einführung, Übungen und Mini-Test."""

import math

from flask import Blueprint, abort, redirect, render_template, request, url_for

from saku.db import einstellung
from saku.lernen import antwort, karten, pfad
from saku.web import db, seite_oder_fragment

bp = Blueprint("michi", __name__, url_prefix="/michi")


def _station_oder_404(con, station_id: int) -> tuple[dict, list[dict]]:
    stationen = pfad.stationen(con)
    station = next((s for s in stationen if s["id"] == station_id), None)
    if station is None:
        abort(404)
    return station, stationen


@bp.get("/")
def index():
    con = db()
    stationen = pfad.stationen(con)
    return render_template("michi/index.html", stationen=stationen, stufen=pfad.STUFEN,
                           aktuell=next((s for s in stationen if s["aktuell"]), None),
                           katalog_leer=not con.execute("SELECT 1 FROM teilaufgabe LIMIT 1").fetchone())


@bp.get("/<int:station_id>")
def station(station_id):
    con = db()
    s, stationen = _station_oder_404(con, station_id)
    letzter = con.execute(
        "SELECT punkte_erreicht, punkte_moeglich, bestanden FROM stationstest WHERE station_id = ? "
        "ORDER BY id DESC LIMIT 1", (station_id,)).fetchone()
    return render_template(
        "michi/station.html", station=s, stationen=stationen, stufen=pfad.STUFEN, letzter=letzter,
        einfuehrung=con.execute("SELECT einfuehrung FROM station WHERE id = ?", (station_id,)).fetchone()[0],
        teilaufgaben=karten.lade(con, pfad.teilaufgaben(con, station_id)),
        aktuell=next((v for v in stationen if v["aktuell"]), None),
        schwelle=float(einstellung(con, "stationstest_schwelle", "0.8")),
    )


@bp.route("/<int:station_id>/test", methods=["GET", "POST"])
def test(station_id):
    con = db()
    s, stationen = _station_oder_404(con, station_id)
    if s["gesperrt"]:  # Der Pfad sperrt nur sich selbst; geübt wird in Keiko
        return redirect(url_for("michi.station", station_id=station_id))
    if request.method == "GET":
        return render_template("michi/test.html", station=s, stationen=stationen,
                               aufgaben=karten.lade(con, pfad.testaufgaben(con, station_id)))

    ids = request.form.getlist("teilaufgabe", type=int)
    # nicht geprüft, also ohne Punkte: anklickbare und SQL mit Sandbox wertet Saku selbst aus
    punkte = {t["id"]: v["punkte"] for t in karten.lade(con, [i for i in ids if not request.form.get(f"punkte-{i}")])
              if (v := antwort.vorschlag(con, t, *_eigene(t)))}
    for t_id in (i for i in ids if i not in punkte):
        try:
            punkte[t_id] = zahl = float((request.form.get(f"punkte-{t_id}") or "0").replace(",", "."))
            if not math.isfinite(zahl):
                raise ValueError
        except ValueError:
            abort(400)
    ergebnis = pfad.test_auswerten(con, station_id, punkte)
    stationen = pfad.stationen(con)
    naechste = next((n for n in stationen if n["position"] > s["position"]), None)
    return seite_oder_fragment("michi/test.html", "michi/_ergebnis.html", station=s, stationen=stationen,
                               ergebnis=ergebnis, naechste=naechste)


def _eigene(t: dict) -> tuple[dict | None, str | None]:
    """Antwort einer Teilaufgabe im Mini-Test: anklickbar (antwort-<id>-…, wie in der Simulation) oder SQL (antwort-<id>)."""
    eingabe = antwort.eingabe(request.form, f"antwort-{t['id']}-") if antwort.pruefbar(t["antwort"]) else None
    return eingabe, request.form.get(f"antwort-{t['id']}")


@bp.post("/<int:station_id>/test/<int:t_id>/pruefen")
def test_pruefen(station_id, t_id):
    """Eine Teilaufgabe im Mini-Test prüfen: Ergebnis, Lösung und vorbelegte Punkte, die änderbar bleiben."""
    con = db()
    station, _ = _station_oder_404(con, station_id)
    t = next(iter(karten.lade(con, [t_id])), None) or abort(404)
    eingabe, eigene = _eigene(t)
    v = antwort.vorschlag(con, t, eingabe, eigene) or abort(400)
    return render_template("michi/_testaufgabe.html", t=t, v=v, eingabe=eingabe, eigene=eigene, station=station)
