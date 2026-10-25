"""Mobil: jede Seite hat das Grundgerüst fürs Handy (viewport-Meta, Tab-Leiste mit „Mehr“), keine festen Breiten in
Inline-Styles und keine Tastenhinweise mitten im Satz, die auf Touch einen halben Satz hinterlassen; dazu gezielte Tests für
mobil behobene Fehler (Demo-Daten)."""

import re
from html.parser import HTMLParser
from pathlib import Path

from saku.lernen import karten
from saku.lernen.rechnen import ARTEN
from tests.test_navigation import KEINE_SEITE

CSS = Path(__file__).parents[1] / "saku" / "web" / "static" / "css"
HTMX = {"HX-Request": "true"}
# feste Breite im style-Attribut (Prozent und eigene Eigenschaften wie --wert sind erlaubt)
FESTE_BREITE = re.compile(r'style="[^"]*(?<![\w-])(?:min-|max-)?width:\s*[\d.]+\s*(?:px|rem|em|ch|vw|pt)', re.I)
LEER = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Tastensaetze(HTMLParser):
    """Findet <kbd class="taste"> im Fließtext (p, li) außerhalb von .nur-tastatur und Bedienelementen: Auf Touch blendet
    saku.css die Taste aus, übrig bliebe „hol dir mit und den Rechenweg“."""

    def __init__(self):
        super().__init__()
        self.stapel, self.funde = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "kbd" and "taste" in (a.get("class") or "").split():
            im_satz = any(t in ("p", "li") for t, _ in self.stapel)
            geschuetzt = any(t in ("button", "a", "summary") or "nur-tastatur" in k or "hilfe-dialog" in k for t, k in self.stapel)
            if im_satz and not geschuetzt:
                self.funde.append(self.getpos())
        if tag not in LEER:
            self.stapel.append((tag, f"{a.get('class') or ''} {a.get('id') or ''}"))

    def handle_startendtag(self, tag, attrs):
        pass  # <use …/> im Icon-Sprite

    def handle_endtag(self, tag):
        while self.stapel and self.stapel.pop()[0] != tag:
            pass


def _seiten(client, con) -> dict[str, str]:
    """Alle GET-Seiten als ganze Seite: Routen ohne Parameter, dazu Station, Mini-Test, jede Rechenart, laufender Sprint,
    Probeprüfung, Simulation und Auswertung, Üben mit SQL-Aufgabe, Themen mit offener Notiz."""
    regeln = [r.rule for r in client.application.url_map.iter_rules()
              if "GET" in r.methods and not r.arguments and r.rule not in KEINE_SEITE and not r.rule.startswith("/static")]
    sim = client.post("/shiken/neu", data={"bereich": "Planen eines Softwareproduktes"}).location
    probe = client.post("/rechnen/probe/neu").location
    sql = con.execute("SELECT id FROM teilaufgabe WHERE typ = 'sql' LIMIT 1").fetchone()[0]
    pfade = [*regeln, "/michi/1", "/michi/1/test", f"/keiko/?teilaufgabe={sql}", "/keiko/?modus=fehler",
             "/niwa/?thema=16", "/rechnen/sprint/neu", sim, probe, *(f"/rechnen/{art}" for art in ARTEN)]
    seiten = {pfad: client.get(pfad, follow_redirects=True).get_data(as_text=True) for pfad in pfade}
    client.post(sim + "/abgeben")
    seiten["auswertung"] = client.get(sim + "/auswertung").get_data(as_text=True)
    return seiten


def test_jede_seite_hat_den_mobilen_rahmen(client, con):
    for pfad, seite in _seiten(client, con).items():
        assert seite.startswith('<!doctype html>'), pfad  # ganze Seite, kein Fragment ohne Rahmen
        assert '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' in seite, pfad
        if pfad != "/willkommen":  # die Einführung hat bewusst keine Leiste
            assert '<nav id="nav" class="nav"' in seite and 'class="nav-mehr' in seite, pfad
        assert not FESTE_BREITE.search(seite), (pfad, FESTE_BREITE.findall(seite))
        leser = Tastensaetze()
        leser.feed(seite)
        assert leser.funde == [], (pfad, leser.funde)


def test_hinweise_nach_dem_pruefen_ohne_halbe_saetze(client):
    """Leer geprüft: der Satz über Esc und Leertaste bleibt auf Touch ganz („… oder hol dir den Rechenweg.“)."""
    for art in ("subnetz", "select", "algorithmus"):
        antwort = client.post(f"/rechnen/{art}/pruefen", data={"seed": "3"}, headers=HTMX).get_data(as_text=True)
        leser = Tastensaetze()
        leser.feed(antwort)
        assert leser.funde == [], art
        assert re.search(r"hol dir (den Rechenweg|die Musterlösung)<span class=\"nur-tastatur\"> mit <kbd", antwort), art


def test_tabellen_brechen_mobil_zu_zeilen_um(client, con):
    """Verlauf, Hochrechnung und die Verläufe von Simulation und Probeprüfung: mobil ohne sichtbaren Tabellenkopf, deshalb
    nennen mehrdeutige Zellen ihren Kopf selbst (data-titel); ohne Punkte entfällt die Zelle mobil statt „Punkte –“."""
    karten.bewerten(con, 1, 3)
    verlauf = client.get("/keiko/verlauf").get_data(as_text=True)
    assert '<thead class="kopf-vorgelesen">' in verlauf and 'data-titel="Punkte"' not in verlauf
    assert 'class="zahl verlauf-rechts verlauf-leer"' in verlauf
    karten.bewerten(con, 2, 2, punkte=2)
    assert 'data-titel="Punkte">2' in client.get("/keiko/verlauf").get_data(as_text=True)

    shiken = client.get("/shiken/").get_data(as_text=True)
    assert shiken.count('<thead class="kopf-vorgelesen">') == 1  # Hochrechnung; ohne Simulation gibt es keinen Verlauf
    assert 'data-titel="Gewicht">' in shiken and 'data-titel="Note">' in shiken
    css = CSS.joinpath("saku.css").read_text(encoding="utf-8")
    assert re.search(r"\[data-titel\]::before \{ content: attr\(data-titel\)", css)


def test_sensei_seite_ohne_tastenspalte_auf_touch(client):
    seite = client.get("/sensei/").get_data(as_text=True)
    tabelle = seite[seite.index('<table class="table sensei-modi">'):seite.index("</table>", seite.index("sensei-modi"))]
    assert tabelle.count("<tr>") == tabelle.count('<tr><td class="nur-tastatur">') == 6
    assert '<span class="nur-tastatur"> (Tasten T, E, P und V)</span>' in seite


def test_eingaben_auf_touch_in_16_px_und_tippflaechen_44_px():
    """iOS zoomt beim Antippen in Felder unter 16 px (Basecoat setzt 14 px); Knöpfe und Felder sind auf Touch 44 px hoch."""
    css = CSS.joinpath("saku.css").read_text(encoding="utf-8")
    block = css[css.index("@media (max-width: 720px), (pointer: coarse) {"):]
    block = block[:block.index("\n}\n")]
    assert "input, select, textarea, .code-zeilen { font-size: max(1rem, 16px) !important; }" in block
    assert re.search(r"\.btn, \.input, \.select[^{]*\{ min-height: 44px; \}", block) and '.btn[data-size^="icon"] { min-width: 44px; }' in block


def test_raster_mit_langen_namen_sprengen_die_karte_nicht():
    """Ohne minmax(0, 1fr) wird eine Grid-Spalte so breit wie ihr längster Name ohne Umbruch: Abdeckung im Fahrplan (504 px
    bei 360 px Breite), Sprint-Aufgaben mit Tabellen, Hochrechnung."""
    for datei, regel in (("heute.css", ".fahrplan-bereich > summary"), ("rechnen.css", ".sprint-aufgabe"), ("shiken.css", ".hochrechnung")):
        css = CSS.joinpath("bereiche", datei).read_text(encoding="utf-8")
        assert re.search(rf"^{re.escape(regel)} \{{ display: grid; grid-template-columns: minmax\(0, 1fr\);", css, re.M), regel
