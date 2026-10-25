"""Navigation: jede Seite ist auffindbar (Seitenleiste, „Alle Seiten“, ⌘K), Unterseiten sind markiert, der mobile Rahmen
hat Tab-Leiste und Blatt „Mehr“ mit den richtigen aria-Attributen (Demo-Daten)."""

import html
import re
from urllib.parse import urlsplit

from flask import url_for

from saku.web import ALLGEMEIN, SEITEN
from saku.web.routen.suche import BEFEHLE

HTMX = {"HX-Request": "true"}
# GET-Routen ohne Parameter, die keine eigene Seite sind
KEINE_SEITE = {
    "/suche/": "die Treffer der Suche selbst, ein Fragment für ⌘K",
    "/fahrplan.ics": "Download, verlinkt auf dem Fahrplan",
    "/einstellungen/lernstand.json": "Download in den Einstellungen",
    "/einstellungen/saku.db": "Download in den Einstellungen, nur im Netz angezeigt",
    "/anmelden": "nur im Netz mit Passwort, sonst eine Weiterleitung",
    "/rechnen/sprint/neu": "startet den Sprint (Weiterleitung), der Knopf steht auf /rechnen/sprint",
    "/rechnen/sprint/lauf": "der laufende Sprint; ohne Aufgaben in der Adresse eine Weiterleitung",
}


def _pfade(text: str) -> set[str]:
    return {urlsplit(html.unescape(h)).path for h in re.findall(r'href="([^"#][^"]*)"', text)}


def test_jede_seite_ist_auffindbar(client, app):
    erreichbar = _pfade(client.get("/").get_data(as_text=True) + client.get("/seiten").get_data(as_text=True))
    with app.test_request_context():
        erreichbar |= {urlsplit(url_for(z[0], **z[1])).path for *_, z in BEFEHLE if z[0] != "einstellung"}
    for regel in app.url_map.iter_rules():
        if "GET" in regel.methods and not regel.arguments and regel.rule not in KEINE_SEITE:
            assert regel.rule in erreichbar, regel.rule


def test_suche_findet_jede_seite_unter_ihrem_namen(client, app):
    with app.test_request_context():
        ziele = [(name, url_for(ziel, **argumente)) for liste in [*SEITEN.values(), ALLGEMEIN] for name, ziel, argumente, _ in liste]
    for name, url in ziele:
        treffer = client.get("/suche/", query_string={"q": name}, headers=HTMX).get_data(as_text=True)
        assert f'href="{html.escape(url)}"' in treffer, name
    assert "Lehrplan" in client.get("/suche/", query_string={"q": "themen"}).get_data(as_text=True)  # Bereich findet Unterseiten
    assert 'href="/seiten"' in client.get("/suche/", query_string={"q": "alle seiten"}).get_data(as_text=True)


def test_unterseiten_in_der_seitenleiste(client, con):
    def nav(url):
        seite = client.get(url).get_data(as_text=True)
        return seite[seite.index('<nav id="nav"'):seite.index("</nav>", seite.index('<nav id="nav"'))]

    fahrplan = nav("/fahrplan")
    assert re.search(r'href="/" title="Heute" aria-current="true"', fahrplan)
    assert '<a href="/fahrplan" aria-current="page">Fahrplan</a>' in fahrplan and 'href="/#woche"' in fahrplan
    assert "Fehlerkorb" not in fahrplan  # nur die Unterseiten des aktiven Bereichs

    fehler = nav("/keiko/?modus=fehler")
    assert '<a href="/keiko/?modus=fehler" aria-current="page">Fehlerkorb</a>' in fehler
    assert re.search(r'href="/keiko/" title="Üben" aria-current="true"', fehler)
    assert re.search(r'href="/keiko/" title="Üben" aria-current="page"', nav("/keiko/"))
    assert 'aria-current="page">Sprint</a>' in nav(client.get("/rechnen/sprint/neu").headers["Location"])  # auch der laufende
    assert 'aria-current="page">Katalog</a>' in nav("/bunseki/?reiter=katalog")

    # WiSo-Schnelltest nur in der AP2
    assert "WiSo-Schnelltest" in nav("/shiken/")
    con.execute("UPDATE einstellung SET wert = 'AP1' WHERE schluessel = 'teil'")
    con.commit()
    assert "WiSo-Schnelltest" not in nav("/shiken/")


def test_reiter_der_analyse_per_adresse(client):
    seite = client.get("/bunseki/?reiter=heatmap").get_data(as_text=True)
    assert 'id="bunseki-tab-heatmap" aria-controls="bunseki-heatmap" aria-selected="true"' in seite
    assert re.search(r'id="bunseki-heatmap" [^>]*class="bunseki-reiter">', seite)
    assert re.search(r'id="bunseki-ueberblick" [^>]*class="bunseki-reiter" hidden>', seite)
    unbekannt = client.get("/bunseki/?reiter=gibtsnicht").get_data(as_text=True)
    assert 'id="bunseki-tab-ueberblick" aria-controls="bunseki-ueberblick" aria-selected="true"' in unbekannt


def test_mobiler_rahmen(client):
    seite = client.get("/").get_data(as_text=True)
    assert "viewport-fit=cover" in seite
    knopf = re.search(r'<button type="button" class="nav-mehr[^"]*"[^>]*>', seite)[0]
    assert 'aria-haspopup="dialog"' in knopf and 'aria-controls="mehr"' in knopf and 'onclick="saku.mehr()"' in knopf
    blatt = seite[seite.index('<dialog id="mehr"'):seite.index("</dialog>", seite.index('<dialog id="mehr"'))]
    assert 'aria-labelledby="mehr-titel"' in blatt and 'id="mehr-titel"' in blatt and 'aria-label="Schließen"' in blatt
    # im Blatt: alle Bereiche mit allen Unterseiten, Umfang, Sensei, Suche, Einstellungen, Alle Seiten
    for text in ("Fahrplan", "Fehlerkorb", "Formelsammlung", "Fachgespräch", "Lehrplan", "KI-Nutzung", "Sensei", "Suche",
                 'href="/einstellungen"', 'href="/seiten"', 'name="teil" value="AP1"', 'name="beruf" value="1202"'):
        assert text in blatt, text
    # geboostete Navigation tauscht das Blatt mit, damit Markierung und Umfang stimmen
    assert 'hx-select-oob="#nav,#fuss,#umfang,#mehr"' in seite
    assert 'id="mehr"' in client.get("/fahrplan", headers={**HTMX, "HX-Boosted": "true"}).get_data(as_text=True)


def test_alle_seiten(client):
    seite = client.get("/seiten").get_data(as_text=True)
    for name, *_, satz in [s for liste in SEITEN.values() for s in liste] + ALLGEMEIN:
        assert f">{html.escape(name)}</span> <span class=\"klein gedaempft\">{html.escape(satz)}</span></a>" in seite, name
    assert 'href="/seiten" title="Alle Seiten" aria-current="page"' in seite
