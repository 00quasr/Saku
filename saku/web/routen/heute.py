"""Heute 今日: Was mache ich jetzt? Tagesziel, Countdown, Prüfungsreife, nächste Station.
Beim ersten Start führt /willkommen einmal durch Saku."""

from datetime import date, datetime, timedelta

from flask import Blueprint, abort, make_response, redirect, render_template, request, url_for

from saku.db import einstellung, setze_einstellung
from saku.lernen import fahrplan, karten, operatoren, pfad, simulation, tagesziel
from saku.web import db
from saku.web.routen.bunseki import dauerbrenner, termin_name

bp = Blueprint("heute", __name__)


def begruessung(stunde: int) -> tuple[str, str]:
    """Japanischer Gruß nach Uhrzeit, immer mit deutscher Übersetzung."""
    if 4 <= stunde < 11:
        return "おはよう", "Guten Morgen"
    if 11 <= stunde < 18:
        return "こんにちは", "Hallo"
    return "こんばんは", "Guten Abend"


WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]


def datum_lang(tag: date) -> str:
    return f"{WOCHENTAGE[tag.weekday()]}, {tag.day}. {MONATE[tag.month - 1]}"


def kalender(con, heute: date, wochen: int = 20) -> list[list[dict]]:
    """Lerntage der letzten Wochen, je Woche Montag bis Sonntag; stufe 0 bis 4 nach Anzahl Bewertungen."""
    tage = {z["tag"]: z["bewertungen"] for z in con.execute("SELECT tag, bewertungen FROM v_lerntage")}
    start = heute - timedelta(days=heute.weekday() + 7 * (wochen - 1))
    raster = []
    for w in range(wochen):
        woche = []
        for d in range(7):
            tag = start + timedelta(days=7 * w + d)
            n = tage.get(tag.isoformat(), 0)
            woche.append({"tag": tag, "n": n, "zukunft": tag > heute,
                          "stufe": 0 if not n else 1 if n < 6 else 2 if n < 16 else 3 if n < 31 else 4})
        raster.append(woche)
    return raster


@bp.get("/")
def index():
    con = db()
    if not con.execute("SELECT 1 FROM teilaufgabe LIMIT 1").fetchone():
        return render_template("heute/index.html", leer=True)
    if einstellung(con, "einfuehrung") != "gesehen":
        if request.headers.get("HX-Request"):  # geboostet aus der Seitenleiste: die Tour braucht die ganze Seite
            antwort = make_response("", 204)
            antwort.headers["HX-Redirect"] = url_for("heute.willkommen")
            return antwort
        return redirect(url_for("heute.willkommen"))
    heute = date.today()
    ziel = tagesziel.tagesziel(con)
    prozent, mankai = tagesziel.pruefungsreife(con)
    stationen = pfad.stationen(con)
    raster = kalender(con, heute)
    # Wo die meisten Punkte noch nicht sitzen: erst Wackeliges, dann große offene Themen
    themen = con.execute(
        "SELECT thema_id, name, punkte_gesamt, punkte_rot, punkte_gelb, punkte_gruen, beherrschung FROM v_thema_lernstand "
        "WHERE ebene = 2 AND punkte_gesamt > 0 "
        "ORDER BY punkte_rot DESC, punkte_gesamt - punkte_gruen - 0.5 * punkte_gelb DESC LIMIT 4").fetchall()
    termin = einstellung(con, tagesziel.termin_schluessel(con))
    return render_template(
        "heute/index.html",
        gruss=begruessung(datetime.now().hour),
        datum=datum_lang(heute),
        datum_iso=heute.isoformat(),
        termin=termin,
        termin_lang=datum_lang(date.fromisoformat(termin)).split(", ")[1] + f" {termin[:4]}" if termin else "",
        reife=con.execute("SELECT neu, rot, gelb, gruen FROM v_pruefungsreife").fetchone(),
        tage=tagesziel.tage_bis_pruefung(con),
        ziel=ziel,
        rot=con.execute("SELECT COUNT(*) FROM karte WHERE status = 'rot' AND teilaufgabe_id IN (SELECT teilaufgabe_id FROM v_teilaufgabe)").fetchone()[0],
        # grobe Schätzung: neue Teilaufgaben brauchen länger als Wiederholungen
        minuten=4 * ziel["neu_offen"] + 2 * ziel["wdh_offen"],
        prozent=prozent,
        mankai=mankai,
        stationen=stationen,
        station=next((s for s in stationen if s["aktuell"]), None),
        lernserie=tagesziel.lernserie(con),
        woche=[t for w in raster[-2:] for t in w if not t["zukunft"]][-7:],
        kalender=raster,
        themen=themen,
        luecken=luecken(con),
        grundwissen=karten.begriffe(con, []),
        laufend=simulation.laufende(con),
    )


@bp.get("/fahrplan", endpoint="fahrplan")  # die Funktion heißt anders als das Modul fahrplan
def fahrplan_seite():
    """Fahrplan bis zur Prüfung: Prognose der Wiederholungen, Tempo, Abdeckung nach Prüfungsgewicht, was am meisten bringt."""
    con = db()
    if not con.execute("SELECT 1 FROM teilaufgabe LIMIT 1").fetchone():
        return render_template("heute/fahrplan.html", leer=True)
    heute = date.today()
    spanne = 30 if request.args.get("tage") == "30" else 14
    ziel = tagesziel.tagesziel(con, heute)
    return render_template(
        "heute/fahrplan.html",
        spanne=spanne,
        tage=tagesziel.tage_bis_pruefung(con, heute),
        lerntage=tagesziel.lerntage(con, heute),
        puffer=einstellung(con, "puffer_tage", "7"),
        ziel=ziel,
        prognose=fahrplan.prognose(con, heute, spanne, ziel),
        tempo=fahrplan.tempo(con, heute),
        abdeckung=fahrplan.abdeckung(con),
        gewinn=fahrplan.gewinn(con),
        termin_name=lambda i: termin_name(i, einstellung(con, "teil") == "AP1"),
    )


def luecken(con) -> list[dict]:
    """Was in Sensei-Bewertungen fehlte, gruppiert nach Operator und Thema; Beispiel ist die jüngste Lücke."""
    zeilen = con.execute(
        "SELECT l.operator, th.id AS thema_id, th.name, COUNT(DISTINCT l.teilaufgabe_id) AS n, MAX(l.id) AS juengste, l.text AS beispiel "
        "FROM luecke l JOIN v_teilaufgabe v ON v.teilaufgabe_id = l.teilaufgabe_id "
        "JOIN teilaufgabe_thema tt ON tt.teilaufgabe_id = l.teilaufgabe_id "
        "JOIN thema u ON u.id = tt.thema_id JOIN thema th ON th.id = COALESCE(CASE u.ebene WHEN 3 THEN u.eltern_id END, u.id) "
        "GROUP BY l.operator, th.id ORDER BY n DESC, juengste DESC LIMIT 4").fetchall()
    return [dict(z) | {"operator": operatoren.OPERATOREN.get(z["operator"], ("Antwort",))[0]} for z in zeilen]


@bp.post("/termin")
def termin():
    """Prüfungstermin direkt auf Heute eintragen."""
    con = db()
    wert = request.form.get("pruefungstermin", "").strip()
    try:
        date.fromisoformat(wert)
    except ValueError:
        abort(400)
    setze_einstellung(con, tagesziel.termin_schluessel(con), wert)
    return redirect(url_for("heute.index"))


def _termin(con) -> dict:
    return {"termin": einstellung(con, tagesziel.termin_schluessel(con)), "tage": tagesziel.tage_bis_pruefung(con),
            "ziel": tagesziel.tagesziel(con), "puffer": einstellung(con, "puffer_tage", "7")}


@bp.get("/willkommen")
def willkommen():
    con = db()
    if not con.execute("SELECT 1 FROM teilaufgabe LIMIT 1").fetchone():
        return redirect(url_for("heute.index"))
    zahlen = con.execute("""SELECT
        (SELECT COUNT(DISTINCT termin_index) FROM v_teilaufgabe) AS termine,
        (SELECT COUNT(*) FROM v_teilaufgabe) AS teilaufgaben,
        (SELECT COUNT(*) FROM v_themen_statistik WHERE ebene = 2 AND teilaufgaben > 0) AS themen,
        (SELECT COUNT(*) FROM v_station) AS stationen""").fetchone()
    # Dauerbrenner nach Punkten: so mischen sich die Prüfungsbereiche, statt dass WiSo mit 100 % vorn liegt
    themen = sorted(dauerbrenner(con), key=lambda t: -t["punkte"])[:5]
    fragen = ([f"Was wurde zu {themen[0]['name']} schon gefragt?"] if themen else []) + [
        "Wie gehe ich an eine Pseudocode-Aufgabe heran?", "Erklär mir die Normalisierung bis zur 3. NF."]
    return render_template("heute/willkommen.html", zahlen=zahlen, themen=themen, fragen=fragen,
                           stationen=pfad.stationen(con)[:4], **_termin(con))


@bp.post("/willkommen/termin")
def willkommen_termin():
    con = db()
    termin = request.form.get("pruefungstermin", "").strip()
    try:
        if termin:
            date.fromisoformat(termin)
    except ValueError:
        abort(400)
    setze_einstellung(con, tagesziel.termin_schluessel(con), termin)
    return render_template("heute/_termin.html", **_termin(con))


@bp.post("/willkommen/umfang")
def willkommen_umfang():
    """Tour: Beruf und Prüfungsteil wählen; zurück kommt, was der Termin dafür bedeutet."""
    con = db()
    for schluessel, erlaubt in (("beruf", ("1201", "1202")), ("teil", ("AP1", "AP2"))):
        wert = request.form.get(schluessel)
        if wert not in erlaubt:
            abort(400)
        setze_einstellung(con, schluessel, wert)
    return render_template("heute/_termin.html", **_termin(con))


@bp.post("/willkommen/fertig")
def willkommen_fertig():
    con = db()
    setze_einstellung(con, "einfuehrung", "gesehen")
    station = next((s for s in pfad.stationen(con) if s["aktuell"]), None)
    if request.form.get("ziel") == "station" and station:
        return redirect(url_for("michi.station", station_id=station["id"]))
    return redirect(url_for("heute.index"))
