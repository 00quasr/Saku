"""Suche ⌘K: Befehle, Sprünge zu Seiten und Themen und Live-Suche über alle Prüfungen."""

from flask import Blueprint, render_template, request

from saku.lernen import rechnen
from saku.sensei import vektoren
from saku.web import ALLGEMEIN, BEREICHE, SEITEN, db, seiten

bp = Blueprint("suche", __name__, url_prefix="/suche")

_TREFFER = """
SELECT v.teilaufgabe_id, v.termin, v.aufgabe_nr, v.kennung, v.status, t.text
FROM {quelle} JOIN v_teilaufgabe v ON v.teilaufgabe_id = s.teilaufgabe_id JOIN teilaufgabe t ON t.id = v.teilaufgabe_id
"""


# Befehlspalette: (Icon, Name, Suchwörter, Ziel). Ziel ist (Endpunkt, Argumente) oder ("einstellung", Schlüssel, Wert);
# die ersten vier stehen schon bei leerer Eingabe da
BEFEHLE = [
    ("timer", "Prüfung simulieren", "simulation shiken test klausur", ("shiken.index", {})),
    ("circle-x", "Fehlerkorb üben", "fehler rot wackelig wiederholen", ("keiko.index", {"modus": "fehler"})),
    ("book-open", "Grundwissen üben", "begriffe karten definitionen vokabeln", ("keiko.grundwissen", {})),
    ("calendar", "Prüfungstermin setzen", "termin datum countdown ihk", ("kern.einstellungen", {"_anchor": "termin"})),
    ("route", "Fahrplan bis zur Prüfung", "prognose tempo wiederholungen abdeckung countdown plan", ("heute.fahrplan", {})),
    ("timer", "WiSo-Schnelltest", "wirtschaft sozialkunde gemischt ankreuzen quiz test simulation", ("shiken.index", {"_anchor": "schnelltest"})),
    ("sparkles", "Neue Teilaufgaben üben", "neu unbekannt", ("keiko.index", {"modus": "neu"})),
    ("star", "Markierte üben", "markiert gemerkt", ("keiko.index", {"modus": "markiert"})),
    ("list-checks", "Verlauf", "bewertungen gemacht erledigt historie protokoll", ("keiko.verlauf", {})),
    ("messages-square", "Fachgespräch üben", "projekt mündlich präsentation prüfer", ("shiken.fachgespraech", {})),
    ("shuffle", "Rechnen: gemischt", "rechentrainer rechenaufgaben üben ap1", ("rechnen.gemischt", {})),
    ("timer", "Rechnen: Sprint mit Note", "sprint zeitlimit prüfung simulation rechentrainer 15 minuten", ("rechnen.sprint", {})),
    ("clipboard-check", "Probeprüfung aus Generatoren", "probe prüfung simulation ap1 rechentrainer 90 minuten note unbegrenzt",
     ("rechnen.probe", {})),
    ("sigma", "Rechnen: Formelsammlung", "formeln spickzettel merksätze drucken rechentrainer", ("rechnen.formeln", {})),
    *(("calculator", f"Rechnen: {a.titel}", f"rechentrainer {a.beschreibung} {' '.join(a.themen)}", ("rechnen.aufgabe", {"art": a.slug}))
      for a in rechnen.ARTEN.values()),
    ("settings", "Einstellungen", "optionen sensei daten", ("kern.einstellungen", {})),
    ("layout-grid", "Alle Seiten", "übersicht navigation inhalt sitemap menü", ("kern.seiten", {})),
    ("briefcase", "Zu Anwendungsentwicklung wechseln", "ae fiae beruf umfang", ("einstellung", "beruf", "1201")),
    ("briefcase", "Zu Systemintegration wechseln", "si fisi beruf umfang", ("einstellung", "beruf", "1202")),
    ("layers", "Zu AP1 wechseln", "teil 1 umfang", ("einstellung", "teil", "AP1")),
    ("layers", "Zu AP2 wechseln", "teil 2 umfang", ("einstellung", "teil", "AP2")),
    ("sun", "Farbschema hell", "hell light farbe", ("einstellung", "farbschema", "hell")),
    ("moon", "Farbschema dunkel", "dunkel dark farbe", ("einstellung", "farbschema", "dunkel")),
    ("monitor", "Farbschema wie System", "system auto farbe", ("einstellung", "farbschema", "system")),
]


def befehle(q: str, teil: str = "AP2") -> list[tuple]:
    """Befehle, deren Name oder Suchwörter alle Wortteile der Anfrage enthalten, ohne Seiten außerhalb des Umfangs."""
    if not q:
        return BEFEHLE[:4]
    woerter, im_umfang = q.casefold().split(), [s[1:3] for liste in seiten(teil).values() for s in liste]
    ausserhalb = [s[1:3] for liste in SEITEN.values() for s in liste if s[1:3] not in im_umfang]
    return [b for b in BEFEHLE if all(w in f"{b[1]} {b[2]}".casefold() for w in woerter) and b[3] not in ausserhalb][:6]


def _like(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def suchen(con, q: str, anzahl: int = 12) -> list:
    """Volltext (Wortteile) und Bedeutung (Vektoren) zusammen, im Umfang; ab vier Zeichen kommt die Bedeutung dazu."""
    worttreffer = _volltext(con, q, anzahl)
    if len(q) < 4:
        return worttreffer
    umfang = {z[0] for z in con.execute("SELECT teilaufgabe_id FROM v_teilaufgabe")}
    nah = [i for i, _ in vektoren.suchen(con, "teilaufgabe", q, n=anzahl, erlaubt=umfang, schwelle=0.4)]
    ids = vektoren.verschmelzen([z["teilaufgabe_id"] for z in worttreffer], nah)[:anzahl]
    if not ids:
        return []
    zeilen = {z["teilaufgabe_id"]: z for z in con.execute(
        _TREFFER.format(quelle="(SELECT id AS teilaufgabe_id FROM teilaufgabe) s") +
        f"WHERE v.teilaufgabe_id IN ({','.join('?' * len(ids))})", ids)}
    return [zeilen[i] for i in ids if i in zeilen]


def _volltext(con, q: str, anzahl: int) -> list:
    """Teilaufgaben zur Suche. Trigramme greifen erst ab 3 Zeichen je Wort, kürzere Anfragen laufen über LIKE."""
    woerter = q.split()
    if woerter and all(len(w) >= 3 for w in woerter):
        ausdruck = " AND ".join('"' + w.replace('"', '""') + '"' for w in woerter)
        return con.execute(_TREFFER.format(quelle="(SELECT teilaufgabe_id, bm25(suche) AS rang FROM suche WHERE suche MATCH ?) s")
                           + "ORDER BY s.rang LIMIT ?", (ausdruck, anzahl)).fetchall()
    muster = _like(q)
    return con.execute(_TREFFER.format(quelle="suche s") + "WHERE s.titel LIKE ?1 ESCAPE '\\' OR s.text LIKE ?1 ESCAPE '\\' "
                       "OR s.loesung LIKE ?1 ESCAPE '\\' ORDER BY v.termin_index DESC, v.aufgabe_nr, v.kennung LIMIT ?2",
                       (muster, anzahl)).fetchall()


def seiten_zu(teil: str, q: str, gezeigt: list = ()) -> list[tuple]:
    """Seiten als (Kanji, Name, Bereich, Ziel), deren Name samt Bereich alle Wortteile enthält; ohne Anfrage nur die
    Bereiche. Was schon als Befehl dasteht (gezeigt), kommt nicht doppelt."""
    alle = [(kanji, name, "" if name == wort else wort, (ziel, argumente))
            for endpunkt, kanji, wort in BEREICHE for name, ziel, argumente, _ in seiten(teil)[endpunkt]]
    alle += [("", name, "", (ziel, argumente)) for name, ziel, argumente, _ in ALLGEMEIN]
    if not q:
        return [s for s in alle if s[0] and not s[2]]
    woerter, ziele = q.casefold().split(), [b[3] for b in gezeigt]
    return [s for s in alle if all(w in " ".join(s[:3]).casefold() for w in woerter) and s[3] not in ziele]


@bp.get("/")
def index():
    q = request.args.get("q", "").strip()[:100]
    con = db()
    teil = con.execute("SELECT teil FROM v_umfang").fetchone()[0]
    if not q:
        return render_template("suche/_treffer.html", q=q, befehle=befehle(q), seiten=seiten_zu(teil, q), themen=[], treffer=[])
    return render_template(
        "suche/_treffer.html", q=q, befehle=befehle(q, teil), seiten=seiten_zu(teil, q, befehle(q, teil)),
        themen=con.execute("SELECT id, name, ebene FROM thema WHERE name LIKE ?1 ESCAPE '\\' OR stichworte LIKE ?1 ESCAPE '\\' "
                           "ORDER BY ebene, position LIMIT 6", (_like(q),)).fetchall(),
        treffer=suchen(con, q),
    )
