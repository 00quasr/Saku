"""Sensei 先生: Tutor-Modi als Server-Sent Events, Antwort prüfen, Punkte vorschlagen, Frag Sensei."""

import base64
import re
import time
import uuid

from flask import Blueprint, Response, abort, current_app, render_template, request, stream_with_context

from saku.db import liste, verbinden
from saku.lernen import operatoren, simulation
from saku.sensei import client, prompts, suche, werkzeuge
from saku.web import db, ganzzahl, markdown_zu_html

bp = Blueprint("sensei", __name__, url_prefix="/sensei")

MODI = {
    "tipp": "Tipp",
    "erklaeren": "Erklären",
    "pruefen": "Antwort prüfen",
    "variante": "Ähnliche Übung",
    "thema": "Thema erklären",
    "chat": "Frag Sensei",
    "fachgespraech": "Fachgespräch",
}
BEWERTUNGEN = {1: "Nicht gewusst", 2: "Teilweise", 3: "Gewusst"}

NICHT_ERREICHBAR = "Sensei ist gerade nicht erreichbar. Der Lösungshinweis bleibt sichtbar, versuch es gleich noch einmal."
PAUSIERT = "Sensei ist während der Simulation pausiert."
OHNE_SCHLUESSEL = "Sensei braucht einen API-Schlüssel: Trag ANTHROPIC_API_KEY in die Datei .env ein und starte Saku neu."

# Offene Anfragen bis der Stream sie abholt; die App läuft lokal, ein Dict reicht
anfragen: dict[str, dict] = {}


def sse(ereignis: str, daten: str) -> str:
    zeilen = "\n".join(f"data: {zeile}" for zeile in daten.split("\n"))
    return f"event: {ereignis}\n{zeilen}\n\n"


def vorschlag(punkte: float, max_punkte: float) -> int:
    """Bewertung, die Sensei vorschlägt: ab 80 % 3 Gewusst, ab 40 % 2 Teilweise, sonst 1."""
    anteil = punkte / max_punkte if max_punkte else 0
    return 3 if anteil >= 0.8 else 2 if anteil >= 0.4 else 1


def pausiert(con) -> bool:
    """Läuft eine Simulation? Abgelaufene beendet laufende() vorher, sonst bliebe Sensei für immer pausiert."""
    return simulation.laufende(con) is not None


@bp.app_context_processor
def panel_kontext():
    return {"sensei_pausiert": lambda: pausiert(db()), "neues_gespraech": lambda: uuid.uuid4().hex}


def _id(name: str) -> int | None:
    return ganzzahl(request.values.get(name, "").strip())


def _meldung(text: str, fehler: bool = False):
    return render_template("sensei/_meldung.html", meldung=text, fehler=fehler)


def _speichern(con, gespraech, rolle, modus, inhalt, teilaufgabe_id=None, thema_id=None) -> None:
    modus = "chat" if modus == "fachgespraech" else modus  # das Gespräch hält die gespraech-ID zusammen; CHECK kennt nur die alten Modi
    con.execute(
        "INSERT INTO sensei_nachricht (gespraech, rolle, modus, inhalt, teilaufgabe_id, thema_id) VALUES (?, ?, ?, ?, ?, ?)",
        (gespraech, rolle, modus, inhalt, teilaufgabe_id, thema_id))
    con.commit()


def _zeichnung(daten_url: str) -> bytes | None:
    """Hochgeladene Zeichnung aus einer data-URL (PNG, JPEG, WebP, höchstens 5 MB), sonst None."""
    treffer = re.fullmatch(r"data:image/(?:png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", daten_url.strip())
    if not treffer:
        return None
    try:
        roh = base64.b64decode(treffer.group(1), validate=True)
    except ValueError:
        return None
    return roh if len(roh) <= 5 * 1024 * 1024 else None


def _bewerten(con, t, antwort: str, rolle: str = "stark", zeichnung: bytes | None = None) -> dict:
    """Antwort gegen den Lösungshinweis prüfen (strukturiert). Der automatische Vorschlag beim Aufdecken nimmt
    das schnelle Modell (ein paar Zehntel Cent), „Prüfen“ (P) das starke."""
    text = (f"{prompts.kontext(con, t)}\n\n{prompts.ANWEISUNG['pruefen']}\n{operatoren.fuer_sensei(t['inhalt'] or t['text'])}"
            f"\n\n<antwort>\n{antwort}\n</antwort>")
    bilder = []
    if zeichnung:
        # Zeichnungen vergleicht das starke Modell: Bild „Zeichnung“ gegen die Lösungshinweise als Bild
        rolle = "stark"
        loesung = [current_app.config["DATEN"] / p for p in liste(t["loesung_bilder"])[:2]]
        bilder = [("Zeichnung", zeichnung)] + [(f"Lösungshinweis {i}", p) for i, p in enumerate(loesung, 1) if p.exists()]
        text += ("\n\nDie Antwort ist eine Zeichnung (Bild „Zeichnung“). Vergleiche sie inhaltlich mit dem Lösungshinweis "
                 "(Text und Bilder „Lösungshinweis“). Ungenaue Handschrift oder Layout kosten keine Punkte, fachliche Fehler schon.")
    b = client.strukturiert(con, "vorschlag" if rolle == "schnell" else "pruefen", rolle, prompts.SYSTEM, text,
                            prompts.BEWERTUNG, max_tokens=1500, bilder=bilder)
    b["max_punkte"] = t["punkte"] or b["max_punkte"]
    b["punkte"] = min(max(b["punkte"], 0), b["max_punkte"])
    # Lücken für Heute: nur die der letzten Bewertung je Teilaufgabe zählen
    ops = operatoren.erkennen(t["inhalt"] or t["text"])
    con.execute("DELETE FROM luecke WHERE teilaufgabe_id = ?", (t["id"],))
    con.executemany("INSERT INTO luecke (teilaufgabe_id, text, operator) VALUES (?, ?, ?)",
                    [(t["id"], f, ops[0]["schluessel"] if ops else None) for f in b["fehlt"] if f.strip()])
    con.commit()
    return b


@bp.get("/")
def index():
    return render_template("sensei/index.html", modi=MODI)


@bp.post("/<modus>")
def anfrage(modus):
    """Legt eine Anfrage an und liefert die leere Sprechblase, die sich per SSE den Text holt."""
    if modus not in MODI:
        abort(404)
    con = db()
    if not current_app.config["SENSEI_BEREIT"]:
        return _meldung(OHNE_SCHLUESSEL)
    if pausiert(con):
        return _meldung(PAUSIERT)

    teilaufgabe_id, thema_id = _id("teilaufgabe"), _id("thema")
    t = prompts.teilaufgabe(con, teilaufgabe_id) if teilaufgabe_id else None
    frage = request.form.get("frage", "").strip()
    if modus in ("tipp", "erklaeren", "pruefen", "variante") and t is None:
        abort(400)
    if modus == "thema" and not (thema_id and con.execute("SELECT 1 FROM thema WHERE id = ?", (thema_id,)).fetchone()):
        abort(400)
    if modus == "chat" and not frage:
        return _meldung("Schreib deine Frage ins Feld, dann antwortet Sensei.")
    if modus == "fachgespraech":
        if not projekt_text():
            return _meldung("Lade zuerst deinen Projektantrag oder deine Dokumentation hoch.")
        frage = frage or "Bitte beginne das Fachgespräch mit deiner ersten Frage."

    gespraech = request.form.get("gespraech", "")
    if modus not in ("chat", "fachgespraech") or not re.fullmatch(r"[0-9a-f]{32}", gespraech):
        gespraech = uuid.uuid4().hex

    if modus == "pruefen":
        antwort = request.form.get("antwort", "").strip()
        zeichnung = _zeichnung(request.form.get("zeichnung", ""))
        if not antwort and not zeichnung:
            return _meldung("Schreib zuerst deine Antwort ins Feld oder lade eine Zeichnung hoch, dann prüft Sensei sie.")
        automatisch = request.form.get("automatisch") == "1"
        try:
            b = _bewerten(con, t, antwort or "(siehe Zeichnung)", "schnell" if automatisch else "stark", zeichnung)
        except client.KiFehler:
            return _meldung(NICHT_ERREICHBAR, fehler=True)
        wert = vorschlag(b["punkte"], b["max_punkte"])
        _speichern(con, gespraech, "user", modus, antwort, teilaufgabe_id)
        _speichern(con, gespraech, "assistant", modus,
                   f"{prompts.zahl(b['punkte'])} von {prompts.zahl(b['max_punkte'])} Punkten. "
                   f"Richtig: {'; '.join(b['richtig']) or '–'}. Fehlt: {'; '.join(b['fehlt']) or '–'}. {b['hinweis']}",
                   teilaufgabe_id)
        return render_template("sensei/_bewertung.html", b=b, wert=wert, wort=BEWERTUNGEN[wert], t_id=teilaufgabe_id,
                               ohne_loesung=not prompts.hat_loesung(t), zahl=prompts.zahl, automatisch=automatisch)

    _speichern(con, gespraech, "user", modus, frage if modus in ("chat", "fachgespraech") else MODI[modus], teilaufgabe_id, thema_id)
    anfrage_id = uuid.uuid4().hex
    anfragen[anfrage_id] = {"modus": modus, "gespraech": gespraech, "frage": frage,
                            "teilaufgabe_id": teilaufgabe_id if t else None, "thema_id": thema_id,
                            "rechnen": t is not None and t["typ"] == "berechnen",
                            "projekt": projekt_text() if modus == "fachgespraech" else ""}
    vorlage = "sensei/_chat.html" if modus in ("chat", "fachgespraech") else "sensei/_blase.html"
    return render_template(vorlage, anfrage_id=anfrage_id, modus=modus, titel=MODI[modus], frage=frage,
                           ohne_loesung=t is not None and modus != "chat" and not prompts.hat_loesung(t),
                           bezug=t and f"{t['termin']} · Aufgabe {t['nummer']} {t['kennung']}")


@bp.post("/punkte")
def punkte():
    """Shiken-Auswertung: Sensei schlägt Punkte vor, übernommen wird nur per Knopf.
    Nicht pausiert: die Auswertung kommt erst nach der Abgabe."""
    con = db()
    t = prompts.teilaufgabe(con, _id("teilaufgabe") or 0)
    feld_id = request.form.get("feld_id", "")
    if t is None or not re.fullmatch(r"[\w-]+", feld_id):
        abort(400)
    if not current_app.config["SENSEI_BEREIT"]:
        return _meldung(OHNE_SCHLUESSEL)
    antwort = request.form.get("antwort", "").strip()
    if not antwort:
        b = {"punkte": 0, "max_punkte": t["punkte"] or 0, "hinweis": "Ohne Antwort gibt es keine Punkte."}
    else:
        try:
            b = _bewerten(con, t, antwort)
        except client.KiFehler:
            return _meldung(NICHT_ERREICHBAR, fehler=True)
    return render_template("sensei/_punkte.html", b=b, feld_id=feld_id, zahl=prompts.zahl)


def _verlauf(con, gespraech: str) -> list[dict]:
    """Bisherige Fragen und Antworten des Gesprächs (ohne die gerade gestellte Frage)."""
    zeilen = con.execute("SELECT rolle, inhalt FROM sensei_nachricht WHERE gespraech = ? ORDER BY id",
                         (gespraech,)).fetchall()[:-1]
    paare = []
    for frage, antwort in zip(zeilen, zeilen[1:]):
        if frage["rolle"] == "user" and antwort["rolle"] == "assistant":
            paare += [{"role": "user", "content": frage["inhalt"]}, {"role": "assistant", "content": antwort["inhalt"]}]
    return paare[-20:]


def projekt_text() -> str:
    """Hochgeladene Projektdokumentation als Text (lokal in data/projekt), leer ohne Upload."""
    pfad = current_app.config["DATEN"] / "projekt" / "text.md"
    return pfad.read_text(encoding="utf-8") if pfad.exists() else ""


def _nachrichten(con, anfrage: dict) -> list[dict]:
    modus = anfrage["modus"]
    if modus == "fachgespraech":
        return [*_verlauf(con, anfrage["gespraech"]), {"role": "user", "content": anfrage["frage"]}]
    if modus == "chat":
        dazu = (anfrage["teilaufgabe_id"],) if anfrage["teilaufgabe_id"] else ()
        frage = anfrage["frage"]
        if anfrage["thema_id"]:
            thema = con.execute("SELECT name FROM thema WHERE id = ?", (anfrage["thema_id"],)).fetchone()
            frage = f"(Ich schaue gerade auf das Thema „{thema['name']}“.)\n{frage}" if thema else frage
        return [*_verlauf(con, anfrage["gespraech"]),
                prompts.nachricht(suche.kontext(con, anfrage["frage"], dazu), f"{prompts.ANWEISUNG['chat']}\n\n{frage}")]
    if modus == "thema":
        return [prompts.nachricht(prompts.thema_kontext(con, anfrage["thema_id"]), prompts.ANWEISUNG["thema"])]
    t = prompts.teilaufgabe(con, anfrage["teilaufgabe_id"])
    return [prompts.nachricht(prompts.kontext(con, t), prompts.ANWEISUNG[modus],
                              prompts.bilder(t, current_app.config["DATEN"]))]


@bp.get("/stream/<anfrage_id>")
def stream(anfrage_id):
    """Antwort als Server-Sent Events: `delta` (bisheriger Text als Markdown-HTML, höchstens alle 80 ms) und am Ende
    `fertig` (Markdown-HTML mit Quellen-Links)."""
    anfrage = anfragen.pop(anfrage_id, None)
    pfad = current_app.config["DB_PFAD"]

    def ereignisse():
        if anfrage is None:
            # Immer mit fertig enden, sonst verbindet sich die SSE-Erweiterung neu
            yield sse("fertig", '<p class="gedaempft">Diese Antwort ist abgelaufen. Frag Sensei einfach noch einmal.</p>')
            return
        con = verbinden(pfad)
        try:
            teile, zuletzt = [], 0.0
            # Rechenaufgaben: Sensei darf Zahlensysteme exakt von Python umrechnen lassen
            ki = werkzeuge.stream if anfrage["rechnen"] else client.stream
            fach = anfrage["modus"] == "fachgespraech"
            system = prompts.fachgespraech_system(anfrage["projekt"]) if fach else prompts.SYSTEM
            for stueck in ki(con, "fachgespraech" if fach else "tutor", system, _nachrichten(con, anfrage)):
                teile.append(stueck)
                # schon beim Schreiben als Markdown zeigen; gedrosselt, sonst rendert der Browser jedes Wort neu
                if time.monotonic() - zuletzt >= 0.08:
                    zuletzt = time.monotonic()
                    yield sse("delta", markdown_zu_html("".join(teile)))
            text = "".join(teile)
            _speichern(con, anfrage["gespraech"], "assistant", anfrage["modus"], text,
                       anfrage["teilaufgabe_id"], anfrage["thema_id"])
            yield sse("fertig", suche.quellen_links(con, markdown_zu_html(text)))
        except client.KiFehler:
            yield sse("fertig", f'<p class="hinweis hinweis--fehler">{NICHT_ERREICHBAR}</p>')
        finally:
            con.close()

    return Response(stream_with_context(ereignisse()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache"})
