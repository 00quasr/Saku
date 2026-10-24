"""Flask-App-Factory: ein Blueprint je Bereich."""

import re
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, abort, current_app, g, render_template, request
from markdown_it import MarkdownIt
from markupsafe import Markup

from saku import config
from saku.db import einstellung, verbinden

BERUFE = {"1201": "Anwendungsentwicklung", "1202": "Systemintegration"}

# (Endpunkt, Kanji, Wort) für die Seitenleiste; Endpunkte heißen intern weiter nach den alten Bereichsnamen
BEREICHE = [
    ("heute.index", "今", "Heute"),
    ("michi.index", "道", "Lernpfad"),
    ("keiko.index", "稽", "Üben"),
    ("rechnen.index", "算", "Rechnen"),
    ("shiken.index", "試", "Prüfung"),
    ("niwa.index", "庭", "Themen"),
    ("bunseki.index", "析", "Analyse"),
]

# Seiten je Bereich für Seitenleiste, Blatt „Mehr“, „Alle Seiten“ und ⌘K: (Name, Endpunkt, Argumente, ein Satz). Die erste
# ist der Bereich selbst; _anchor springt zu einem Abschnitt der Seite, reiter öffnet einen Reiter der Analyse
SEITEN = {
    "heute.index": [
        ("Heute", "heute.index", {}, "Tagesplan, Prüfungsreife, Lernserie und wo die Punkte liegen."),
        ("Fahrplan", "heute.fahrplan", {}, "Prognose bis zur Prüfung, Meilensteine und Lern-Termine für deinen Kalender."),
        ("Wochenrückblick", "heute.index", {"_anchor": "woche"}, "Die letzten sieben Tage im Vergleich zur Woche davor."),
    ],
    "michi.index": [
        ("Lernpfad", "michi.index", {}, "Die Themen als Stationen in sinnvoller Reihenfolge, jede mit Einführung und Mini-Test."),
    ],
    "keiko.index": [
        ("Üben", "keiko.index", {}, "Eine Teilaufgabe nach der anderen, fällige Wiederholungen zuerst."),
        ("Fehlerkorb", "keiko.index", {"modus": "fehler"}, "Was zuletzt nicht saß, so lange, bis es sitzt."),
        ("Markierte", "keiko.index", {"modus": "markiert"}, "Die Teilaufgaben, die du dir gemerkt hast."),
        ("Grundwissen", "keiko.grundwissen", {}, "Fachbegriffe als Karten, auch umgekehrt: Definition lesen, Begriff wählen."),
        ("Verlauf", "keiko.verlauf", {}, "Alle Bewertungen nach Tagen, oben der Wochenrückblick."),
    ],
    "rechnen.index": [
        ("Rechnen", "rechnen.index", {}, "Jede Rechenart der Prüfung, unbegrenzt neu erzeugt und sofort geprüft."),
        ("Sprint", "rechnen.sprint", {}, "Fünf Rechenaufgaben in 15 Minuten, mit Punkten und Note."),
        ("Probeprüfung", "rechnen.probe", {}, "Eine ganze Prüfung aus den Generatoren, mit Uhr, Punkten und Note."),
        ("Formelsammlung", "rechnen.formeln", {}, "Formeln und Merksätze zum Nachschlagen und Drucken."),
    ],
    "shiken.index": [
        ("Prüfung", "shiken.index", {}, "Simulation aus Aufgaben verschiedener Jahrgänge, mit Note und Stempel."),
        ("WiSo-Schnelltest", "shiken.index", {"_anchor": "schnelltest"}, "Anklickbare WiSo-Teilaufgaben quer durch alle Termine, sofort ausgewertet."),
        ("Fachgespräch", "shiken.fachgespraech", {}, "Sensei fragt wie ein Prüfer zu deinem Projekt."),
        ("Hochrechnung", "shiken.index", {"_anchor": "hochrechnung"}, "Deine Gesamtnote nach der Ausbildungsverordnung."),
    ],
    "niwa.index": [
        ("Themen", "niwa.index", {}, "Wissensgraph aus Themen, Lernfeldern und Fachbegriffen."),
        ("Lehrplan", "niwa.index", {"_anchor": "lehrplan-titel"}, "Die Lernfelder des Rahmenlehrplans und wie oft ihre Themen drankamen."),
        ("Alle Themen", "niwa.index", {"_anchor": "themen-titel"}, "Jedes Thema mit Wachstumsstufe, Sicherheit und Punkten."),
    ],
    "bunseki.index": [
        ("Analyse", "bunseki.index", {}, "Was in den Prüfungen drankam: Dauerbrenner, Lücken, nie Geprüftes."),
        ("Katalog", "bunseki.index", {"reiter": "katalog"}, "Alle Inhalte der IHK-Prüfungskataloge als Checkliste."),
        ("Heatmap", "bunseki.index", {"reiter": "heatmap"}, "Welches Thema an welchem Termin wie viele Punkte brachte."),
        ("Inventar", "bunseki.index", {"reiter": "inventar"}, "Alle erfassten Prüfungen mit Teilaufgaben und Lösungshinweisen."),
        ("KI-Nutzung", "bunseki.index", {"reiter": "ki"}, "Alle Aufrufe der Claude-API aus Pipeline und Sensei."),
    ],
}
# Seiten außerhalb der Bereiche
ALLGEMEIN = [
    ("Sensei", "sensei.index", {}, "Frag nach allem aus den Prüfungen; als Panel geht das überall."),
    ("Einstellungen", "kern.einstellungen", {}, "Prüfungstermine, Tagesziele, eigene Noten, Farbschema und Sicherung."),
    ("Einführung", "heute.willkommen", {}, "Der Rundgang vom ersten Start, noch einmal."),
]


def seiten(teil: str) -> dict:
    """SEITEN im Umfang: den WiSo-Schnelltest gibt es nur in der AP2."""
    return {b: [s for s in liste if teil == "AP2" or s[0] != "WiSo-Schnelltest"] for b, liste in SEITEN.items()}


def unterseite(liste: list) -> tuple | None:
    """Die Unterseite eines Bereichs, auf der man gerade ist: Endpunkt (auch Sprint-Lauf und Heft der Probeprüfung) und
    Argumente passen. Sprungmarken liegen auf der Seite des Bereichs selbst und zählen nicht."""
    return next((s for s in liste[1:] if "_anchor" not in s[2] and (request.endpoint or "").startswith(s[1])
                 and all(request.args.get(k) == v for k, v in s[2].items())), None)


def db():
    """Datenbankverbindung für die laufende Anfrage."""
    if "db" not in g:
        g.db = verbinden(current_app.config["DB_PFAD"])
    return g.db


_markdown = MarkdownIt("commonmark", {"html": False}).enable("table")


def markdown_zu_html(text: str | None) -> Markup:
    """Markdown (z. B. von Sensei) als HTML; eingebettetes HTML wird angezeigt, nicht ausgeführt.
    Einzige Ausnahme: <br> – Markdown-Tabellen kennen keinen Zeilenumbruch in Zellen, Claude schreibt dort <br>."""
    return Markup(re.sub(r"&lt;br\s*/?&gt;", "<br>", _markdown.render(text or ""), flags=re.I))


def klartext(text: str | None) -> str:
    """Markdown ohne Zeichen für Auszüge in Listen: **fett**, `code`, # Überschrift, Tabellenstriche, Bilder."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text or "")
    text = re.sub(r"(\*\*|__|`+|^#+\s*|^\s*[-*]\s+|\|)", " ", text, flags=re.M)
    return re.sub(r"\s+", " ", text.replace("<br>", " ")).strip()


def ist_fragment() -> bool:
    """htmx-Anfrage, die nur ein Stück HTML austauscht (geboostete Links wollen die ganze Seite)."""
    return request.headers.get("HX-Request") == "true" and request.headers.get("HX-Boosted") != "true"


def seite_oder_fragment(seite: str, fragment: str, **kontext) -> str:
    return render_template(fragment if ist_fragment() else seite, **kontext)


def ganzzahl(text: str | None) -> int | None:
    """Nicht negative Ganzzahl aus Adresse oder Formular, sonst None. Nicht str.isdigit(): das lässt „²“ durch, int() aber
    nicht, und mehr als 4.300 Ziffern nimmt int() auch nicht; beides wäre Fehler 500 statt einer ungültigen Eingabe."""
    try:
        return int(text) if text and text.isdecimal() else None
    except ValueError:
        return None


def create_app(daten: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["DATEN"] = daten or config.DATEN
    app.config["DB_PFAD"] = config.db_pfad(app.config["DATEN"])
    app.config["SENSEI_BEREIT"] = bool(config.API_KEY)
    app.config["FENSTER"] = False  # True im eigenen App-Fenster (python -m saku start)
    # DNS-Rebinding: eine fremde Seite, deren Name auf 127.0.0.1 zeigt, gälte im Browser als gleiche Herkunft und könnte
    # Lernstand lesen und Sensei (API-Kosten) aufrufen – Flask beantwortet jeden anderen Host-Namen mit 400
    app.config["TRUSTED_HOSTS"] = ["127.0.0.1", "localhost"]  # Saku lauscht nur auf IPv4

    from saku.web.routen import bunseki, heute, keiko, kern, michi, niwa, rechnen, sensei, shiken, suche
    for modul in (kern, heute, michi, keiko, rechnen, shiken, niwa, sensei, bunseki, suche):
        app.register_blueprint(modul.bp)

    app.add_template_filter(markdown_zu_html, "markdown")
    app.add_template_filter(klartext, "klartext")
    from saku.lernen import antwort
    app.add_template_filter(antwort.tabelle, "tabelle")
    app.add_template_filter(antwort.als_text, "antwort_als_text")
    app.add_template_global(antwort.pruefbar, "pruefbar")
    from saku.lernen import rechnen
    app.add_template_global(rechnen.denkfehler, "denkfehler")
    from saku.lernen import operatoren
    app.add_template_filter(operatoren.erkennen, "operatoren")
    from saku.lernen.tagesziel import ihk_termine
    app.add_template_global(ihk_termine, "ihk_termine")
    from saku.lernen import simulation

    @app.template_global()
    def ihk_note(erreicht: float, moeglich: float) -> str:
        """„Note 3 · befriedigend“ nach dem IHK-Notenschlüssel."""
        n = simulation.note(simulation.umrechnen(erreicht, moeglich))
        return f"Note {n} · {simulation.NOTEN[n]}"

    @app.template_filter("quellen")
    def quellen(html: str) -> Markup:
        """[T123] in KI-Texten → Link auf die Teilaufgabe in Keiko."""
        from saku.sensei.suche import quellen_links
        return quellen_links(db(), html)

    @app.before_request
    def gleiche_herkunft():
        """Schreibende Anfragen nur von Saku selbst."""
        # CSRF: Saku lauscht auf localhost, eine fremde Webseite im Browser könnte sonst Bewertungen oder Einstellungen schicken
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return
        seite = request.headers.get("Sec-Fetch-Site")
        herkunft = request.headers.get("Origin")
        if (seite is not None and seite not in ("same-origin", "none")) or \
                (herkunft is not None and urlsplit(herkunft).netloc.lower() != request.host.lower()):
            abort(403)

    @app.errorhandler(OverflowError)
    def zahl_zu_gross(fehler):
        """Ganzzahlen aus Adresse oder Formular (type=int) sind unbegrenzt, SQLite speichert höchstens 2^63: eine Seed,
        Teilaufgabe oder Startzeit darüber ist eine ungültige Eingabe, kein Absturz. Andere Überläufe bleiben Fehler."""
        if "SQLite INTEGER" not in str(fehler):
            raise fehler
        return "Zahl zu groß", 400

    @app.teardown_appcontext
    def schliessen(_fehler):
        con = g.pop("db", None)
        if con is not None:
            con.close()

    @app.context_processor
    def kontext():
        from saku.web.routen.suche import befehle, seiten_zu
        umfang = db().execute("SELECT beruf, teil FROM v_umfang").fetchone()
        im_umfang = seiten(umfang["teil"])
        return {
            "befehle_start": befehle(""),
            "seiten_start": seiten_zu(umfang["teil"], ""),
            "BEREICHE": BEREICHE,
            "SEITEN": im_umfang,
            "ALLGEMEIN": ALLGEMEIN,
            "bereich": request.blueprint,
            "unterseite": unterseite(im_umfang.get(f"{request.blueprint}.index", [])),
            "farbschema": einstellung(db(), "farbschema", "dunkel"),
            "sensei_bereit": app.config["SENSEI_BEREIT"],
            "faellig": db().execute("SELECT COUNT(*) FROM v_faellig").fetchone()[0],
            "umfang": umfang,
            "BERUFE": BERUFE,
        }

    return app
