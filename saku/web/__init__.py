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


def create_app(daten: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["DATEN"] = daten or config.DATEN
    app.config["DB_PFAD"] = config.db_pfad(app.config["DATEN"])
    app.config["SENSEI_BEREIT"] = bool(config.API_KEY)
    app.config["FENSTER"] = False  # True im eigenen App-Fenster (python -m saku start)

    from saku.web.routen import bunseki, heute, keiko, kern, michi, niwa, rechnen, sensei, shiken, suche
    for modul in (kern, heute, michi, keiko, rechnen, shiken, niwa, sensei, bunseki, suche):
        app.register_blueprint(modul.bp)

    app.add_template_filter(markdown_zu_html, "markdown")
    app.add_template_filter(klartext, "klartext")
    from saku.lernen import antwort
    app.add_template_filter(antwort.tabelle, "tabelle")
    app.add_template_filter(antwort.als_text, "antwort_als_text")
    app.add_template_global(antwort.pruefbar, "pruefbar")
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
        from saku.web.routen.suche import befehle
        return {
            "befehle_start": befehle(""),
            "BEREICHE": BEREICHE,
            "bereich": request.blueprint,
            "farbschema": einstellung(db(), "farbschema", "dunkel"),
            "sensei_bereit": app.config["SENSEI_BEREIT"],
            "faellig": db().execute("SELECT COUNT(*) FROM v_faellig").fetchone()[0],
            "umfang": db().execute("SELECT beruf, teil FROM v_umfang").fetchone(),
            "BERUFE": BERUFE,
        }

    return app
