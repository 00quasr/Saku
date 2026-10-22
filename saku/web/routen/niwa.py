"""Niwa 庭: der Wissensgraph aller Themen, Lernfelder und Fachbegriffe, dazu je Knoten eine Notiz."""

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for

from saku import niwa
from saku.sensei import client
from saku.web import db, ist_fragment

bp = Blueprint("niwa", __name__, url_prefix="/niwa")

UMFANG = "SELECT teilaufgabe_id FROM v_teilaufgabe"


def _thema(thema_id: int) -> dict:
    con = db()
    lernstand = con.execute("SELECT * FROM v_thema_lernstand WHERE thema_id = ?", (thema_id,)).fetchone()
    if lernstand is None:
        abort(404)
    teilaufgaben = con.execute(
        "SELECT v.teilaufgabe_id, v.termin, v.aufgabe_nr, v.kennung, v.punkte, v.status, t.text "
        "FROM v_zuordnung z JOIN v_teilaufgabe v ON v.teilaufgabe_id = z.teilaufgabe_id "
        "JOIN teilaufgabe t ON t.id = z.teilaufgabe_id "
        "WHERE z.thema_id = ? ORDER BY v.termin_index DESC, v.aufgabe_nr, v.kennung", (thema_id,)).fetchall()
    return {
        "thema": lernstand, "teilaufgaben": teilaufgaben, "stufen": niwa.STUFEN,
        "wissen": con.execute("SELECT beschreibung FROM thema WHERE id = ?", (thema_id,)).fetchone()[0],
        "lernfelder": con.execute("SELECT lf.* FROM thema_lernfeld tl JOIN lernfeld lf ON lf.id = tl.lernfeld_id "
                                  "WHERE tl.thema_id = ? ORDER BY lf.id", (thema_id,)).fetchall(),
        "begriffe": con.execute(
            f"SELECT b.id, b.name, COUNT(*) AS n FROM v_zuordnung z JOIN teilaufgabe_begriff tb ON tb.teilaufgabe_id = z.teilaufgabe_id "
            f"JOIN begriff b ON b.id = tb.begriff_id WHERE z.thema_id = ? AND z.teilaufgabe_id IN ({UMFANG}) "
            f"GROUP BY b.id ORDER BY n DESC, b.name LIMIT 16", (thema_id,)).fetchall(),
        "voraussetzungen": con.execute("SELECT th.id, th.name FROM thema_voraussetzung tv JOIN thema th ON th.id = tv.voraussetzung_id "
                                       "WHERE tv.thema_id = ? ORDER BY th.name", (thema_id,)).fetchall(),
    }


@bp.get("/")
def index():
    con = db()
    daten = niwa.graph(con)
    daten["pulsieren"] = niwa.aufgeblueht(con, daten)
    thema_id, begriff_id = request.args.get("thema", type=int), request.args.get("begriff", type=int)
    return render_template("niwa/index.html", daten=daten, themen=niwa.themen(con), stufen=niwa.STUFEN, lehrplan=niwa.lehrplan(con),
                           auswahl=f"t{thema_id}" if thema_id else f"b{begriff_id}" if begriff_id else None)


@bp.get("/thema/<int:thema_id>")
def thema(thema_id):
    if not ist_fragment():
        return redirect(url_for("niwa.index", thema=thema_id))
    return render_template("niwa/_thema.html", **_thema(thema_id))


@bp.get("/begriff/<int:begriff_id>")
def begriff(begriff_id):
    con = db()
    b = con.execute("SELECT * FROM begriff WHERE id = ?", (begriff_id,)).fetchone()
    if b is None:
        abort(404)
    return render_template(
        "niwa/_begriff.html", begriff=b,
        fundstellen=con.execute(
            "SELECT v.teilaufgabe_id, v.termin, v.aufgabe_nr, v.kennung, v.status, t.text FROM teilaufgabe_begriff tb "
            "JOIN v_teilaufgabe v ON v.teilaufgabe_id = tb.teilaufgabe_id JOIN teilaufgabe t ON t.id = tb.teilaufgabe_id "
            "WHERE tb.begriff_id = ? ORDER BY v.termin_index DESC, v.aufgabe_nr, v.kennung", (begriff_id,)).fetchall(),
        themen=con.execute(
            f"SELECT th.id, th.name, COUNT(*) AS n FROM teilaufgabe_begriff tb JOIN teilaufgabe_thema tt ON tt.teilaufgabe_id = tb.teilaufgabe_id "
            f"JOIN thema th ON th.id = tt.thema_id WHERE tb.begriff_id = ? AND tb.teilaufgabe_id IN ({UMFANG}) "
            f"GROUP BY th.id ORDER BY n DESC LIMIT 6", (begriff_id,)).fetchall(),
        verwandt=con.execute(
            f"SELECT b.id, b.name, COUNT(*) AS n FROM teilaufgabe_begriff x JOIN teilaufgabe_begriff y "
            f"ON y.teilaufgabe_id = x.teilaufgabe_id AND y.begriff_id <> x.begriff_id JOIN begriff b ON b.id = y.begriff_id "
            f"WHERE x.begriff_id = ? AND x.teilaufgabe_id IN ({UMFANG}) GROUP BY b.id ORDER BY n DESC, b.name LIMIT 14",
            (begriff_id,)).fetchall())


@bp.post("/begriff/<int:begriff_id>/erklaeren")
def erklaeren(begriff_id):
    """Sensei erklärt einen Begriff in wenigen Sätzen; die Erklärung bleibt gespeichert."""
    con = db()
    b = con.execute("SELECT * FROM begriff WHERE id = ?", (begriff_id,)).fetchone()
    if b is None:
        abort(404)
    if not b["erklaerung"]:
        if not current_app.config["SENSEI_BEREIT"]:
            return render_template("sensei/_meldung.html", meldung="Sensei ist aus: Es fehlt der API-Schlüssel.", fehler=True)
        beispiele = "\n".join(f"- {z[0][:300]}" for z in con.execute(
            "SELECT t.text FROM teilaufgabe_begriff tb JOIN teilaufgabe t ON t.id = tb.teilaufgabe_id "
            "WHERE tb.begriff_id = ? LIMIT 3", (begriff_id,)))
        try:
            antwort = client.strukturiert(
                con, "begriff", "schnell",
                "Du erklärst Fachbegriffe für Auszubildende (Fachinformatiker/-in) kurz vor der IHK-Prüfung: 3 bis 5 Sätze "
                "Markdown, präzise, mit einem Beispiel aus der Praxis. Keine Einleitung, keine Floskeln.",
                f"Begriff: {b['name']}\nSo kam er in Prüfungen vor:\n{beispiele}",
                {"type": "object", "properties": {"erklaerung": {"type": "string"}}, "required": ["erklaerung"],
                 "additionalProperties": False}, max_tokens=1500)
        except client.KiFehler as fehler:
            return render_template("sensei/_meldung.html", meldung=str(fehler), fehler=True)
        con.execute("UPDATE begriff SET erklaerung = ? WHERE id = ?", (antwort["erklaerung"], begriff_id))
        con.commit()
        b = con.execute("SELECT * FROM begriff WHERE id = ?", (begriff_id,)).fetchone()
    return render_template("niwa/_erklaerung.html", begriff=b)


@bp.get("/lernfeld/<int:lernfeld_id>")
def lernfeld(lernfeld_id):
    con = db()
    feld = next((f for f in niwa.lehrplan(con) if f["id"] == lernfeld_id), None)
    if feld is None:
        abort(404)
    return render_template("niwa/_lernfeld.html", feld=feld)
