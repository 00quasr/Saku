"""Bereichsübergreifend: Bildausschnitte aus data/aufgaben und Einstellungen."""

import json
import sqlite3
from datetime import date, datetime

from flask import Blueprint, abort, current_app, redirect, render_template, request, send_from_directory, url_for

from saku import config
from saku.db import einstellung, letzte_sicherung, setze_einstellung, sichern
from saku.web import db

bp = Blueprint("kern", __name__)

FARBSCHEMAS = {"system": "System", "hell": "Hell", "dunkel": "Dunkel"}


@bp.get("/bild/<path:pfad>")
def bild(pfad):
    """Bildausschnitt; pfad wie in der Datenbank, z. B. aufgaben/3f2a…/2b-1.png"""
    if not pfad.startswith("aufgaben/"):
        abort(404)
    # send_from_directory verhindert Pfade außerhalb von data/aufgaben (auch über ../)
    return send_from_directory(current_app.config["DATEN"] / "aufgaben", pfad.removeprefix("aufgaben/"))


# Jede Einstellung speichert einzeln beim Ändern; der Prüfer sagt, ob der Wert gültig ist
FELDER = {
    "pruefungstermin": lambda w: w == "" or date.fromisoformat(w),
    "pruefungstermin_ap1": lambda w: w == "" or date.fromisoformat(w),
    "beruf": lambda w: w in ("1201", "1202"),
    "teil": lambda w: w in ("AP1", "AP2"),
    # eigene Punkte (0–100) für die Hochrechnung; leer = Saku schätzt
    **{f"note_{k}": (lambda w: w == "" or 0 <= float(w.replace(",", ".")) <= 100) for k in ("ap1", "projekt", "pb2", "pb3", "wiso")},
    "puffer_tage": lambda w: w.isdigit() and int(w) <= 60,
    "stationstest_schwelle": lambda w: 0.5 <= float(w) <= 1,
    "farbschema": lambda w: w in FARBSCHEMAS,
}


def termin_info(con, schluessel: str) -> str:
    termin = einstellung(con, schluessel)
    tage = (date.fromisoformat(termin) - date.today()).days if termin else None
    if tage is None:
        return "Noch kein Termin: Saku plant dann ein festes Tagesziel."
    if tage < 0:
        return "Dieser Termin liegt hinter dir."
    return f"Noch {tage} {'Tag' if tage == 1 else 'Tage'}."


@bp.get("/einstellungen")
def einstellungen():
    con = db()
    zahlen = con.execute("""SELECT
        (SELECT COUNT(DISTINCT pruefung_id) FROM v_teilaufgabe) AS pruefungen,
        (SELECT COUNT(*) FROM v_teilaufgabe) AS teilaufgaben,
        (SELECT COUNT(*) FROM teilaufgabe WHERE loesung_text IS NOT NULL OR loesung_bilder <> '[]') AS mit_loesung,
        (SELECT COUNT(*) FROM v_themen_statistik WHERE ebene = 2 AND teilaufgaben > 0) AS themen""").fetchone()
    ki = con.execute("SELECT COALESCE(SUM(aufrufe), 0) AS aufrufe, COALESCE(SUM(aus_cache), 0) AS aus_cache, "
                     "COALESCE(SUM(tokens_ein), 0) AS tokens_ein, COALESCE(SUM(tokens_aus), 0) AS tokens_aus "
                     "FROM v_ki_nutzung").fetchone()
    return render_template(
        "einstellungen.html",
        werte={k: einstellung(con, k, "") for k in FELDER},
        termin_info={k: termin_info(con, k) for k in ("pruefungstermin", "pruefungstermin_ap1")},
        farbschemas=FARBSCHEMAS,
        modelle=config.MODELLE,
        zahlen=zahlen,
        ki=ki,
        sicherung=sicherung_info(),
    )


def sicherung_info() -> str:
    datei = letzte_sicherung(current_app.config["DB_PFAD"])
    if not datei:
        return "Noch keine Sicherung. Saku sichert beim Start einmal am Tag."
    return f"Zuletzt am {datetime.fromtimestamp(datei.stat().st_mtime):%d.%m.%Y um %H:%M}: data/backups/{datei.name}"


@bp.get("/einstellungen/lernstand.json")
def lernstand_export():
    from saku.lernen import lernstand
    return json.dumps(lernstand.exportieren(db()), ensure_ascii=False, indent=1), 200, {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": f"attachment; filename=saku-lernstand-{date.today().isoformat()}.json"}


@bp.post("/einstellungen/sichern")
def jetzt_sichern():
    try:
        sichern(current_app.config["DB_PFAD"], erzwingen=True)
    except (OSError, sqlite3.Error) as fehler:
        return f"Sicherung fehlgeschlagen: {fehler}"
    return sicherung_info()


@bp.post("/einstellungen/<schluessel>")
def speichern(schluessel):
    con = db()
    wert = request.form.get(schluessel, "").strip()
    try:
        gueltig = schluessel in FELDER and FELDER[schluessel](wert)
    except ValueError:
        gueltig = False
    if not gueltig:
        abort(400)
    setze_einstellung(con, schluessel, wert.replace(",", ".") if schluessel.startswith("note_") else wert)
    if schluessel in ("beruf", "teil") or schluessel.startswith("note_"):  # ändert, was die Seite zeigt
        return "", 200, {"HX-Refresh": "true"}
    # der Termin zeigt gleich, was er bedeutet; alles andere meldet nur „Gespeichert“
    text = termin_info(con, schluessel) if schluessel.startswith("pruefungstermin") else ""
    return text, 200, {"HX-Trigger": "gespeichert"}


@bp.post("/umfang")
def umfang():
    """Schalter in der Seitenleiste: Beruf oder Prüfungsteil wechseln, dann zurück zur Seite."""
    con = db()
    for schluessel in ("beruf", "teil"):
        if wert := request.form.get(schluessel):
            if not FELDER[schluessel](wert):
                abort(400)
            setze_einstellung(con, schluessel, wert)
    zurueck = request.referrer or ""
    return redirect(zurueck if zurueck.startswith(request.host_url) else url_for("heute.index"))
