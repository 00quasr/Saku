"""Tastatur und Screenreader: die Hilfe nennt jede Taste, Rückmeldungen nach htmx-Tausch werden angesagt (Demo-Daten)."""

import re
from pathlib import Path

TEMPLATES = Path(__file__).parents[1] / "saku" / "web" / "templates"
ZEICHEN = {" ": "␣", "Enter": "↵", "ArrowLeft": "←", "ArrowRight": "→"}


def test_hilfe_nennt_jede_taste(client):
    html = client.get("/").get_data(as_text=True)
    hilfe = html[html.index('id="hilfe-dialog"'):html.index("</dialog>", html.index('id="hilfe-dialog"'))]
    tasten = {t for datei in TEMPLATES.rglob("*.html") for t in re.findall(r'data-taste="([^"{]+)"', datei.read_text(encoding="utf-8"))}
    assert {"Enter", " ", "u", "m", "s"} <= tasten
    for taste in tasten:
        assert f'<kbd class="taste">{ZEICHEN.get(taste, taste.upper())}</kbd>' in hilfe, taste
    for zeile in ("Grundwissen", "Rechenweg zeigen", "Sprint", "Verlauf: alle", "SQL in der Sandbox ausführen"):
        assert zeile in hilfe


HTMX = {"HX-Request": "true"}


def _bezuege(html: str) -> None:
    """Jede id in aria-labelledby und aria-describedby gibt es in derselben Antwort."""
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    for bezug in re.findall(r'aria-(?:labelledby|describedby)="([^"]+)"', html):
        assert set(bezug.split()) <= ids, bezug


def test_fokus_und_ansagen_nach_dem_tausch(client, con):
    # Grundwissen umgekehrt: die neue Karte bekommt den Fokus und heißt „Rückmeldung, Frage, Definition“
    for name, teilaufgabe in (("Rekursion", 8), ("Bubblesort", 6)):
        b = con.execute("INSERT INTO begriff (name, slug, erklaerung) VALUES (?, ?, 'Erfundene Erklärung.')", (name, name.lower())).lastrowid
        con.execute("INSERT INTO teilaufgabe_begriff VALUES (?, ?)", (teilaufgabe, b))
    con.commit()
    karte = client.get("/keiko/grundwissen?modus=umgekehrt").get_data(as_text=True)
    _bezuege(karte)
    b_id = re.search(r"/keiko/grundwissen/(\d+)/bewerten", karte)[1]
    danach = client.post(f"/keiko/grundwissen/{b_id}/bewerten", data={"wahl": b_id}, headers=HTMX).get_data(as_text=True)
    assert 'tabindex="-1" autofocus' in danach and 'aria-labelledby="begriff-eben begriff-frage begriff-definition"' in danach
    _bezuege(danach)

    # Rechnen: nach dem Prüfen liegt der Fokus auf „Nächste Aufgabe“, das Urteil beschreibt den Knopf
    auswertung = client.post("/rechnen/subnetz/pruefen", data={"seed": "3", "aufgeben": "1"}, headers=HTMX).get_data(as_text=True)
    assert 'autofocus aria-describedby="rechnen-urteil"' in auswertung and 'id="rechnen-urteil" role="status"' in auswertung
    _bezuege(auswertung)

    # Fahrplan: der Umschalter hat nach dem Tausch dieselbe id, htmx setzt den Fokus wieder darauf
    fahrplan = client.get("/fahrplan").get_data(as_text=True)
    assert 'id="prognose-14"' in fahrplan and 'aria-label="Wiederholungen und neue Teilaufgaben je Tag"' in fahrplan
    assert 'id="prognose-30"' in client.get("/fahrplan?tage=30", headers=HTMX).get_data(as_text=True)
    _bezuege(fahrplan)

    # Mini-Test: „Prüfen“ nennt die Teilaufgabe; danach Fokus auf die vorbelegten Punkte mit dem Hinweis als Beschreibung
    con.executemany("INSERT INTO stationstest (station_id, bestanden) VALUES (?, 1)", [(1,), (2,), (4,)])
    con.commit()
    test = client.get("/michi/5/test").get_data(as_text=True)
    assert 'aria-describedby="testaufgabe-9"' in test
    _bezuege(test)
    geprueft = client.post("/michi/5/test/9/pruefen", data={"antwort-9": "SELECT 1"}, headers=HTMX).get_data(as_text=True)
    assert re.search(r'id="punkte-9"[^>]*aria-describedby="auto-9" autofocus', geprueft)
    _bezuege(geprueft)

    # SQL in Üben: angesagt wird die Meldung, die Tabelle nicht Zelle für Zelle
    ergebnis = client.post("/keiko/9/sql", data={"antwort": "SELECT * FROM lager"}).get_data(as_text=True)
    assert '<figure class="sql-tabelle" aria-live="off">' in ergebnis and "3 Zeilen" in ergebnis
    assert 'id="sql-ergebnis" class="sql-ergebnis" aria-live="polite"' in client.get("/keiko/?teilaufgabe=9").get_data(as_text=True)


def test_geteilte_bausteine_stehen_in_saku_css():
    """Was mehrere Bereiche nutzen, steht in saku.css; eine Bereichsdatei, die so eine Klasse ohne Bereichsbezug neu definiert,
    gestaltet alle Bereiche um (so machte .verlauf aus rechnen.css einmal die ganze Verlauf-Seite zur Zeile)."""
    css = Path(__file__).parents[1] / "saku" / "web" / "static" / "css"
    gemeinsam = css.joinpath("saku.css").read_text(encoding="utf-8")
    for klasse in ("segment", "shiken-auto", "shiken-antwort", "rechnen-link", "verlauf", "verlauf-punkt", "bunseki-versteckt"):
        assert re.search(rf"^\.{klasse}[\s{{>\[.:-]", gemeinsam, re.M), klasse
        for datei in css.joinpath("bereiche").glob("*.css"):
            assert not re.search(rf"^\.{klasse}(?![\w-])", datei.read_text(encoding="utf-8"), re.M), (klasse, datei.name)
