"""Bereichsübergreifend: Bildausschnitte aus data/aufgaben, Einstellungen (mit Sicherung, im Netz Paket und Datenbank)
und „Alle Seiten“."""

import json
import os
import sqlite3
import tempfile
import threading
from datetime import date, datetime

from flask import Blueprint, abort, current_app, redirect, render_template, request, send_file, send_from_directory, url_for

from saku import config, paket
from saku.db import einstellung, kopieren, letzte_sicherung, setze_einstellung, sichern
from saku.web import db
from saku.web.routen.bunseki import THEMEN_ZAHLEN
from saku.web.routen.heute import NEU_IN_SAKU

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
    "rechnen_ziel": lambda w: w.isdigit() and int(w) <= 50,  # Rechenaufgaben am Tag, 0 = aus
    "farbschema": lambda w: w in FARBSCHEMAS,
    "neu_gesehen": lambda w: w == NEU_IN_SAKU,  # „Neu in Saku“ auf Heute weggeklickt
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
    zahlen = con.execute(f"""SELECT
        (SELECT COUNT(DISTINCT pruefung_id) FROM v_teilaufgabe) AS pruefungen,
        (SELECT COUNT(*) FROM v_teilaufgabe) AS teilaufgaben,
        (SELECT COUNT(*) FROM teilaufgabe WHERE loesung_text IS NOT NULL OR loesung_bilder <> '[]') AS mit_loesung,
        {THEMEN_ZAHLEN}""").fetchone()
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


@bp.get("/einstellungen/saku.db")
def datenbank_herunterladen():
    """Stimmige Kopie der Datenbank, als Sicherung nach Hause; die Kopie ist gelöscht, sobald sie gesendet ist."""
    fd, pfad = tempfile.mkstemp(suffix=".db", dir=current_app.config["DATEN"])  # neben der Datenbank: auf dem Volume
    os.close(fd)
    try:
        kopieren(current_app.config["DB_PFAD"], pfad)
        datei = open(pfad, "rb")
    finally:
        os.unlink(pfad)  # die offene Datei liest send_file trotzdem zu Ende
    return send_file(datei, mimetype="application/vnd.sqlite3", as_attachment=True,
                     download_name=f"saku-{date.today().isoformat()}.db")


_einspielen = threading.Lock()


@bp.post("/einstellungen/paket")
def paket_hochladen():
    """Paket aus python -m saku paket, nur im Netz: roh im Rumpf statt als Formular, damit es in Blöcken direkt auf den
    Datenträger neben der Datenbank geht (das Volume) und nicht erst ins Temp-Verzeichnis des Containers."""
    if not (current_app.config["SERVER"] and current_app.config["PASSWORT"]):
        abort(404)
    if (request.content_length or 0) > paket.GRENZE:
        return "Das Paket ist zu groß.", 413
    if not _einspielen.acquire(blocking=False):
        return "Es wird gerade schon ein Paket übernommen.", 409
    daten = current_app.config["DATEN"]
    teil = daten / ".paket.teil"
    try:
        groesse = 0
        with open(teil, "wb") as datei:
            while block := request.stream.read(1024 * 1024):
                groesse += len(block)
                if groesse > paket.GRENZE:
                    return "Das Paket ist zu groß.", 413
                datei.write(block)
        zahlen = paket.einspielen(teil, daten)
    except ValueError as fehler:
        return str(fehler), 400
    except (OSError, sqlite3.Error) as fehler:
        return f"Übernahme fehlgeschlagen: {fehler}", 500
    finally:
        teil.unlink(missing_ok=True)
        _einspielen.release()
    behalten = sum(uebernommen for uebernommen, _ in zahlen.values())
    return f"Paket übernommen. Vom Lernstand hier kamen {behalten} Einträge dazu, die alte Datenbank liegt in backups/."


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


@bp.get("/seiten")
def seiten():
    """Alle Seiten nach Bereich, je mit einem Satz; erreichbar aus der Seitenleiste, dem Blatt „Mehr“ und mit ⌘K."""
    return render_template("seiten.html")
