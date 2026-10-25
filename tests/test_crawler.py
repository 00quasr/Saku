"""Link-Crawler als Regressionstest: ab / jeden internen Link (href, hx-get, src, srcset, Knoten im Wissensgraph)
besuchen, als Seite, geboostet und als Fragment. Kein Link darf ins Leere (404) oder auf einen Fehler (500) führen.
Dazu je Bereich ein billiger POST-Rundgang, danach noch einmal crawlen, weil Verlauf, Simulation und Rechnen erst mit
Daten mehr zeigen (Demo-Daten, erfundene Prüfungen)."""

import html
import re
from collections import deque
from urllib.parse import urljoin, urlsplit

import pytest

from saku.lernen import rechnen
from saku.sensei import client as ki

LINK = re.compile(r'\b(href|hx-get|src|srcset)="([^"]*)"')
# Knoten im Wissensgraph: saku.js lädt die Notiz per htmx.ajax nach /niwa/<art>/<nr>
KNOTEN = re.compile(r'(?:data-knoten="|"id": ")(t|lf|b)(\d+)"')
NIWA = {"t": "thema", "lf": "lernfeld", "b": "begriff"}
SEITE = {}
GEBOOSTET = {"HX-Request": "true", "HX-Boosted": "true"}
FRAGMENT = {"HX-Request": "true"}
JE_PFAD = 3  # Query-Varianten je Pfad, sonst crawlt man jede Rechenaufgabe einzeln


@pytest.fixture(autouse=True)
def ohne_ki(monkeypatch):
    """Der Crawler klickt alles an, darf aber nie Claude aufrufen."""
    def verboten(*_a, **_k):
        raise AssertionError("KI-Aufruf im Crawler")
    for name in ("_api", "_claude_code", "stream", "strukturiert"):
        monkeypatch.setattr(ki, name, verboten)


def _links(seite: str, text: str) -> list[tuple[str, dict]]:
    """Interne Links einer Antwort mit den Headern, mit denen der Browser sie abrufen würde."""
    links = []
    for art, wert in LINK.findall(text):
        for teil in wert.split(",") if art == "srcset" else [wert]:
            url = urljoin(seite, html.unescape(teil.split()[0] if teil.strip() else "")).split("#")[0]
            if not url.startswith("/") or url.startswith("//"):
                continue
            links.append((url, FRAGMENT if art == "hx-get" else SEITE))
            if art == "href" and not url.startswith("/static/"):
                links.append((url, GEBOOSTET))
    links += [(f"/niwa/{NIWA[art]}/{nr}", FRAGMENT) for art, nr in KNOTEN.findall(text)]
    return links


def crawlen(client, start: list[tuple[str, dict]] | None = None) -> dict[str, int]:
    """Breitensuche über alle internen Links ab / (und start): {"GET url Header": Status}; Weiterleitungen werden mitverfolgt."""
    gesehen, je_pfad, status = set(), {}, {}
    # dazu jede GET-Route ohne Parameter: manche Seiten erreicht man nur per JavaScript (Sensei, Suche)
    routen = [(r.rule, SEITE) for r in client.application.url_map.iter_rules() if "GET" in r.methods and not r.arguments]
    schlange = deque([("/", SEITE), *routen, *(start or [])])
    while schlange:
        url, kopf = schlange.popleft()
        schluessel = (url, tuple(kopf))
        teile = urlsplit(url)
        if schluessel in gesehen:
            continue
        if teile.query:
            varianten = je_pfad.setdefault((teile.path, tuple(kopf)), set())
            if len(varianten) >= JE_PFAD and url not in varianten:
                continue
            varianten.add(url)
        gesehen.add(schluessel)
        antwort = client.get(url, headers=kopf)
        status[f"GET {url} {'+'.join(kopf) or 'Seite'}"] = antwort.status_code
        if antwort.status_code in (301, 302, 303):
            schlange.append((antwort.headers["Location"], SEITE))
        elif antwort.mimetype == "text/html":
            schlange.extend(_links(url, antwort.get_data(as_text=True)))
        if antwort.headers.get("HX-Redirect"):
            schlange.append((antwort.headers["HX-Redirect"], SEITE))
    return status


def _kaputt(status: dict[str, int]) -> list[str]:
    return [f"{s} {anfrage}" for anfrage, s in status.items() if s >= 400]


ZUSTAENDE = {
    "frisch": [],
    "AP1 ohne Termin": ["UPDATE einstellung SET wert = 'AP1' WHERE schluessel = 'teil'"],  # die Demo hat nur AP2
    "Termin vorbei": ["UPDATE einstellung SET wert = '2020-01-01' WHERE schluessel = 'pruefungstermin'"],
    "leerer Katalog": ["DELETE FROM pruefung", "DELETE FROM station", "DELETE FROM thema"],
}


@pytest.mark.parametrize("zustand", ZUSTAENDE)
def test_alle_links(client, con, zustand):
    for anweisung in ZUSTAENDE[zustand]:
        con.execute(anweisung)
    con.commit()
    status = crawlen(client)
    assert len(status) > 60  # wirklich gecrawlt, nicht nach der Startseite stehengeblieben
    assert _kaputt(status) == []


def _wissen(con) -> int:
    """Erfundene Begriffe mit Erklärung und ein Lernfeld (die Demo hat keine): Grundwissen, Begriffs- und Lernfeld-Notizen."""
    ids = []
    for name, erklaerung, teilaufgabe in (("Gesamtpuffer", "Zeit, um die sich ein Vorgang verschieben darf.", 2),
                                          ("Rekursion", "Eine Funktion ruft sich selbst auf.", 8)):
        ids.append(con.execute("INSERT INTO begriff (name, slug, erklaerung) VALUES (?, ?, ?)",
                               (name, name.lower(), erklaerung)).lastrowid)
        con.execute("INSERT INTO teilaufgabe_begriff VALUES (?, ?)", (teilaufgabe, ids[-1]))
    lf = con.execute("INSERT INTO lernfeld (nummer, titel, jahr) VALUES ('5', 'Demo: Daten verwalten', 2)").lastrowid
    con.execute("INSERT INTO thema_lernfeld SELECT id, ? FROM thema WHERE name = 'Datenbanken'", (lf,))
    con.commit()
    return ids[0]


def test_post_rundgang_und_alle_links_mit_daten(client, con):
    """Je Bereich die billigen POSTs, dann alles noch einmal crawlen, auch die Links aus den POST-Antworten."""
    links = []
    begriff = _wissen(con)

    def post(url, daten=None, kopf=FRAGMENT):
        antwort = client.post(url, data=daten or {}, headers=kopf)
        assert antwort.status_code < 400, (url, antwort.status_code)
        links.extend(_links(url, antwort.get_data(as_text=True)))
        return antwort

    # Üben: bewerten, markieren, überspringen, zurück, SQL ausführen und prüfen
    t_id = re.search(r'data-sensei-teilaufgabe="(\d+)"', client.get("/keiko/").get_data(as_text=True))[1]
    runde = []
    for ergebnis in (3, 1, 2):
        html = post(f"/keiko/{t_id}/bewerten", {"ergebnis": ergebnis, "runde": ",".join(runde)}).get_data(as_text=True)
        runde.append(t_id)
        t_id = re.search(r'data-sensei-teilaufgabe="(\d+)"', html)[1]
    post(f"/keiko/{t_id}/markieren")
    post(f"/keiko/{t_id}/ueberspringen", {"modus": "neu", "runde": ",".join(runde)})
    post("/keiko/zurueck", {"runde": ",".join(runde)})
    sql = con.execute("SELECT id FROM teilaufgabe WHERE loesung_sql IS NOT NULL").fetchone()[0]
    post(f"/keiko/{sql}/sql", {"antwort": "SELECT * FROM lager"})
    post(f"/keiko/{sql}/pruefen", {"antwort": "SELECT 1"})

    post(f"/keiko/grundwissen/{begriff}/bewerten", {"ergebnis": "3"})

    # Rechnen: jede Art einmal mit Eingaben und einmal „Rechenweg zeigen“
    for art in rechnen.ARTEN:
        felder = re.findall(r'name="(feld-[^"]+)"', client.get(f"/rechnen/{art}?seed=7").get_data(as_text=True))
        assert felder, art
        post(f"/rechnen/{art}/pruefen", {"seed": "7", **{f: "1" for f in felder}})
        post(f"/rechnen/{art}/pruefen", {"seed": "8", "aufgeben": "1", "gemischt": "1"})

    # Simulation: anlegen, Antwort speichern, abgeben, auswerten
    url = post("/shiken/neu", {"bereich": "Planen eines Softwareproduktes"}, SEITE).headers["Location"]
    ids = re.findall(r'name="antwort-(\d+)"', client.get(url).get_data(as_text=True))
    post(url + "/speichern", {f"antwort-{ids[0]}": "Kritischer Pfad: A-C-E"})
    post(url + "/abgeben", kopf=SEITE)
    post(url + "/auswertung", {f"punkte-{i}": "2" for i in ids}, SEITE)

    # Probeprüfung aus den Generatoren: anlegen, zwischenspeichern, abgeben
    url = post("/rechnen/probe/neu", kopf=SEITE).headers["Location"]
    felder = re.findall(r'name="(a\d+-[^"]+)"', client.get(url).get_data(as_text=True))
    assert felder
    post(url + "/speichern", {f: "1" for f in felder})
    post(url + "/abgeben", {f: "1" for f in felder}, SEITE)

    # Lernpfad: Mini-Test der ersten Station
    test = client.get("/michi/1/test").get_data(as_text=True)
    ids = re.findall(r'name="teilaufgabe" value="(\d+)"', test)
    post("/michi/1/test", {"teilaufgabe": ids, **{f"punkte-{i}": "1" for i in ids}})

    # Einstellungen, Termin, Umfang, Einführung und die Korrektur der Zuordnung in der Analyse
    for schluessel, wert in {"farbschema": "hell", "puffer_tage": "5", "stationstest_schwelle": "0.7",
                             "pruefungstermin": "2027-04-28", "note_projekt": "75", "teil": "AP2", "beruf": "1201"}.items():
        post(f"/einstellungen/{schluessel}", {schluessel: wert})
    post("/einstellungen/sichern")
    post("/termin", {"pruefungstermin": "2027-04-28"}, SEITE)
    post("/umfang", {"teil": "AP2"}, SEITE)
    post("/willkommen/termin", {"pruefungstermin": "2027-04-28"})
    post("/willkommen/umfang", {"beruf": "1201", "teil": "AP2"})
    post("/willkommen/fertig", {"ziel": "heute"}, SEITE)
    unterthema = con.execute("SELECT id FROM thema WHERE ebene = 3").fetchone()[0]
    post("/bunseki/zuordnung/1", {"thema": unterthema})

    status = crawlen(client, links)
    for pfad in ("/niwa/begriff/", "/niwa/lernfeld/", "/keiko/verlauf", "/shiken/1/auswertung", "/rechnen/", "/rechnen/probe/1"):
        assert any(pfad in anfrage for anfrage in status), pfad  # mit Daten kommt der Crawler wirklich dorthin
    assert _kaputt(status) == []
