"""Shiken 試験: Prüfungssimulation mit Timer, Selbstbewertung, Note und Stempel."""

import math
import uuid
from datetime import datetime
from itertools import groupby
from pathlib import Path

import pymupdf
from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for

from saku.lernen import hochrechnung, karten, simulation
from saku.web import db

bp = Blueprint("shiken", __name__, url_prefix="/shiken")


def _simulation_oder_404(con, sim_id: int):
    simulation.laufende(con)  # beendet abgelaufene Simulationen
    sim = con.execute("SELECT * FROM simulation WHERE id = ?", (sim_id,)).fetchone()
    if sim is None:
        abort(404)
    return sim


def _teilaufgaben(con, sim_id: int) -> list[dict]:
    """Die Teilaufgaben der Simulation samt eigener Antwort und vergebener Punkte.
    „eigene“, nicht „antwort“: antwort ist das Antwortformat der Teilaufgabe (Optionen, Vorlage)."""
    zeilen = con.execute("SELECT teilaufgabe_id, antwort, punkte_erreicht FROM simulation_teilaufgabe "
                         "WHERE simulation_id = ? ORDER BY position", (sim_id,)).fetchall()
    eigenes = {z["teilaufgabe_id"]: dict(z) for z in zeilen}
    return [t | {"eigene": eigenes[t["id"]]["antwort"], "erreicht": eigenes[t["id"]]["punkte_erreicht"]}
            for t in karten.lade(con, list(eigenes))]


def _antworten_speichern(con, sim) -> None:
    """Antworten bleiben änderbar, bis die Simulation ausgewertet ist (auch kurz nach Ablauf der Zeit)."""
    if sim["note"] is not None:
        return
    con.executemany(
        "UPDATE simulation_teilaufgabe SET antwort = ? WHERE simulation_id = ? AND teilaufgabe_id = ?",
        [(wert if wert.strip() else None, sim["id"], int(name[8:]))  # Einrückung bleibt (Pseudocode)
         for name, wert in request.form.items() if name.startswith("antwort-") and name[8:].isdigit()])
    con.commit()


@bp.get("/")
def index():
    con = db()
    laufend = simulation.laufende(con)  # zuerst, damit abgelaufene im Verlauf schon beendet sind
    bereiche = []
    for z in con.execute("SELECT bereich, COUNT(DISTINCT pruefung_id) AS pruefungen FROM v_teilaufgabe "
                         "GROUP BY bereich ORDER BY bereich").fetchall():
        dauer, aufgaben = simulation.aufbau(con, z["bereich"])
        bereiche.append(dict(z) | {"dauer": dauer, "aufgaben": aufgaben})
    verlauf = [dict(s) | {"punkte_100": simulation.umrechnen(s["punkte_erreicht"] or 0, s["punkte_moeglich"] or 0)}
               for s in con.execute("SELECT *, strftime('%d.%m.%Y', gestartet_am, 'localtime') AS datum "
                                    "FROM simulation ORDER BY id DESC").fetchall()]
    return render_template("shiken/index.html", bereiche=bereiche, verlauf=verlauf, laufend=laufend,
                           noten=simulation.NOTEN, hochrechnung=hochrechnung.stand(con))


@bp.post("/neu")
def neu():
    con = db()
    if laufend := simulation.laufende(con):
        return redirect(url_for("shiken.simulation", sim_id=laufend["id"]))
    try:
        sim_id = simulation.zusammenstellen(con, request.form.get("bereich", ""))
    except ValueError:
        abort(400)
    return redirect(url_for("shiken.simulation", sim_id=sim_id))


@bp.get("/<int:sim_id>", endpoint="simulation")
def ansehen(sim_id):
    con = db()
    sim = _simulation_oder_404(con, sim_id)
    if sim["beendet_am"]:
        return redirect(url_for("shiken.auswertung", sim_id=sim_id))
    rest = con.execute(
        "SELECT CAST((julianday(gestartet_am, '+' || dauer_min || ' minutes') - julianday('now')) * 86400 AS INTEGER) "
        "FROM simulation WHERE id = ?", (sim_id,)).fetchone()[0]
    teilaufgaben = _teilaufgaben(con, sim_id)
    return render_template("shiken/simulation.html", sim=sim, rest=max(0, rest),
                           aufgaben=[list(g) for _, g in groupby(teilaufgaben, key=lambda t: t["aufgabe_id"])])


@bp.post("/<int:sim_id>/speichern")
def speichern(sim_id):
    con = db()
    _antworten_speichern(con, _simulation_oder_404(con, sim_id))
    return f"Gespeichert um {datetime.now():%H:%M}"


@bp.post("/<int:sim_id>/abgeben")
def abgeben(sim_id):
    con = db()
    _antworten_speichern(con, _simulation_oder_404(con, sim_id))
    con.execute("UPDATE simulation SET beendet_am = COALESCE(beendet_am, datetime('now')) WHERE id = ?", (sim_id,))
    con.commit()
    return redirect(url_for("shiken.auswertung", sim_id=sim_id))


@bp.route("/<int:sim_id>/auswertung", methods=["GET", "POST"])
def auswertung(sim_id):
    con = db()
    sim = _simulation_oder_404(con, sim_id)
    if not sim["beendet_am"]:
        return redirect(url_for("shiken.simulation", sim_id=sim_id))
    if request.method == "POST":
        if sim["note"] is None:  # nur einmal auswerten, sonst zählten die Bewertungen doppelt
            punkte = {}
            for name, wert in request.form.items():
                if name.startswith("punkte-") and name[7:].isdigit():
                    try:
                        punkte[int(name[7:])] = zahl = float((wert or "0").replace(",", "."))
                        if not math.isfinite(zahl):  # „nan“ nimmt float() an, die Note bräche dann ab
                            raise ValueError
                    except ValueError:
                        abort(400)
            simulation.auswerten(con, sim_id, punkte)
        return redirect(url_for("shiken.auswertung", sim_id=sim_id))

    punkte_100 = simulation.umrechnen(sim["punkte_erreicht"] or 0, sim["punkte_moeglich"] or 0)
    return render_template(
        "shiken/auswertung.html", sim=sim, teilaufgaben=_teilaufgaben(con, sim_id), punkte_100=punkte_100,
        noten=simulation.NOTEN, kosten=simulation.kosten(con, sim_id) if sim["note"] is not None else [])


# --- Fachgespräch: Projektdokumentation hochladen, Sensei fragt wie ein Prüfer ----------------------------------

def _projekt_ordner():
    return current_app.config["DATEN"] / "projekt"


@bp.get("/fachgespraech")
def fachgespraech():
    from saku.web.routen.sensei import projekt_text
    text = projekt_text()
    name = (_projekt_ordner() / "name.txt").read_text(encoding="utf-8") if (_projekt_ordner() / "name.txt").exists() else ""
    return render_template("shiken/fachgespraech.html", projekt=text, projekt_name=name,
                           woerter=len(text.split()), gespraech=uuid.uuid4().hex)


@bp.post("/fachgespraech/projekt")
def projekt_hochladen():
    """PDF, Markdown oder Text bis 20 MB; gespeichert wird nur der Text (lokal in data/projekt, nie im Repo)."""
    datei = request.files.get("datei")
    if not datei or not datei.filename:
        abort(400)
    roh = datei.read(20 * 1024 * 1024 + 1)
    if len(roh) > 20 * 1024 * 1024:
        abort(413)
    if datei.filename.lower().endswith(".pdf"):
        try:
            with pymupdf.open(stream=roh, filetype="pdf") as doc:
                text = "\n\n".join(seite.get_text() for seite in doc)
        except (RuntimeError, ValueError):
            abort(400)
    elif datei.filename.lower().endswith((".md", ".txt")):
        text = roh.decode("utf-8", errors="replace")
    else:
        abort(400)
    if not text.strip():
        abort(400)  # z. B. ein gescanntes PDF ohne Textebene
    ordner = _projekt_ordner()
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "text.md").write_text(text, encoding="utf-8")
    (ordner / "name.txt").write_text(Path(datei.filename).name, encoding="utf-8")
    return redirect(url_for("shiken.fachgespraech"))


@bp.post("/fachgespraech/projekt/entfernen")
def projekt_entfernen():
    for name in ("text.md", "name.txt"):
        (_projekt_ordner() / name).unlink(missing_ok=True)
    return redirect(url_for("shiken.fachgespraech"))
