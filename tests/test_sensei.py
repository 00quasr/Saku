"""Sensei: Prompt-Aufbau, SSE, Vorschlagsregel, Quellen-Links, RAG-Suche, Pause. Die API ist immer gemockt."""

import re

import pytest
from flask import render_template_string

from saku.sensei import client as ki
from saku.sensei import prompts, suche
from saku.web.routen import sensei as route


def teilaufgabe_id(con, text_anfang: str) -> int:
    return con.execute("SELECT id FROM teilaufgabe WHERE text LIKE ?", (text_anfang + "%",)).fetchone()[0]


@pytest.fixture
def bereit(app):
    app.config["SENSEI_BEREIT"] = True
    return app


@pytest.fixture
def ki_mock(monkeypatch):
    """Ersetzt stream und strukturiert; merkt sich die Aufrufe."""
    aufrufe = {"stream": [], "strukturiert": []}
    antworten = {"stream": ["Denk an ", "<b>Puffer</b>", "\n\nSiehe [T1]."],
                 "pruefen": {"punkte": 5, "max_punkte": 6, "richtig": ["Pfad genannt"], "fehlt": ["Dauer"], "hinweis": "Nenne die Dauer."},
                 "suche": {"begriffe": ["Normalform", "ab", "Tabelle"]}}

    def stream(con, zweck, system, nachrichten, **kw):
        aufrufe["stream"].append({"zweck": zweck, "system": system, "nachrichten": nachrichten})
        if isinstance(antworten["stream"], Exception):
            raise antworten["stream"]
        yield from antworten["stream"]

    def strukturiert(con, zweck, rolle, system, text, schema, **kw):
        aufrufe["strukturiert"].append({"zweck": zweck, "rolle": rolle, "text": text, "schema": schema, "bilder": kw.get("bilder", [])})
        return dict(antworten["pruefen" if zweck == "vorschlag" else zweck])

    monkeypatch.setattr(ki, "stream", stream)
    monkeypatch.setattr(ki, "strukturiert", strukturiert)
    return aufrufe, antworten


def ereignisse(text: str) -> list[tuple[str, str]]:
    """SSE-Text → [(ereignis, daten)]"""
    liste = []
    for block in text.strip().split("\n\n"):
        zeilen = block.split("\n")
        liste.append((zeilen[0].removeprefix("event: "), "\n".join(z.removeprefix("data: ") for z in zeilen[1:])))
    return liste


# --- Prompt-Aufbau -----------------------------------------------------------

def test_kontextblock(con):
    t = prompts.teilaufgabe(con, teilaufgabe_id(con, "Ermitteln Sie den kritischen Pfad"))
    text = prompts.kontext(con, t)
    assert text.startswith(f'<aufgabe kennung="T{t["id"]}" termin="Sommer 2023" '
                           'bereich="Planen eines Softwareproduktes" punkte="6" thema="Netzplan">')
    for teil in ("<ausgangssituation>Erfundene Ausgangssituation", "<einleitung>Die Demo GmbH plant",
                 "<teilaufgabe>Ermitteln Sie den kritischen Pfad", "<loesungshinweis>Kritischer Pfad: A-C-E-F"):
        assert teil in text
    assert prompts.kontext(con, t) == text  # byte-stabil fürs Prompt-Caching


def test_kontext_ohne_loesung(con):
    tid = teilaufgabe_id(con, "Ermitteln Sie den kritischen Pfad")
    con.execute("UPDATE teilaufgabe SET loesung_text = NULL, loesung_bilder = '[]' WHERE id = ?", (tid,))
    t = prompts.teilaufgabe(con, tid)
    assert prompts.OHNE_LOESUNG in prompts.kontext(con, t)
    assert not prompts.hat_loesung(t)


def test_nachricht_kontext_vor_anweisung():
    n = prompts.nachricht("<aufgabe/>", prompts.ANWEISUNG["tipp"], [{"type": "image"}])
    assert [b["type"] for b in n["content"]] == ["image", "text", "text"]
    assert n["content"][1] == {"type": "text", "text": "<aufgabe/>", "cache_control": {"type": "ephemeral"}}
    assert n["content"][2]["text"].startswith("Gib genau einen Denkanstoß")
    assert "Denkanstoß" not in prompts.SYSTEM  # Modus wechselt, der Systemprompt nicht


def test_thema_kontext(con):
    datenbanken = con.execute("SELECT id FROM thema WHERE name = 'Datenbanken'").fetchone()[0]
    text = prompts.thema_kontext(con, datenbanken)
    assert text.startswith('<thema name="Datenbanken">')
    assert text.count("<aufgabe ") == 4
    assert prompts.thema_kontext(con, 9999) is None


def test_bewertungsschema_streng():
    assert prompts.BEWERTUNG["additionalProperties"] is False
    assert set(prompts.BEWERTUNG["required"]) == set(prompts.BEWERTUNG["properties"])


# --- Regeln ------------------------------------------------------------------

def test_sse_format():
    assert route.sse("delta", "Hallo") == "event: delta\ndata: Hallo\n\n"
    assert route.sse("fertig", "<p>a</p>\n<p>b</p>") == "event: fertig\ndata: <p>a</p>\ndata: <p>b</p>\n\n"


@pytest.mark.parametrize("punkte, erwartet", [(10, 3), (8, 3), (7.9, 2), (4, 2), (3.9, 1), (0, 1)])
def test_vorschlag_80_40(punkte, erwartet):
    assert route.vorschlag(punkte, 10) == erwartet


def test_vorschlag_ohne_maximum():
    assert route.vorschlag(3, 0) == 1


def test_quellen_links(con):
    eins, zwei = teilaufgabe_id(con, "Ermitteln Sie"), teilaufgabe_id(con, "Berechnen Sie den Gesamtpuffer")
    html = str(suche.quellen_links(con, f"<p>Siehe [T{eins}] und [T{zwei}, T9999]. Unbekannt: [T9999]</p>"))
    assert f'<a class="quelle" href="/keiko/?teilaufgabe={eins}">Sommer 2023 · Aufgabe 1 a</a>' in html
    assert f'href="/keiko/?teilaufgabe={zwei}">Sommer 2023 · Aufgabe 1 b</a> T9999' in html
    assert html.endswith("Unbekannt: [T9999]</p>")


# --- RAG-Suche ---------------------------------------------------------------

def test_suchbegriffe_und_treffer(con, ki_mock):
    aufrufe, _ = ki_mock
    begriffe = suche.suchbegriffe(con, "Wie normalisiere ich eine Tabelle?")
    assert begriffe == ["Normalform", "Tabelle"]  # zu kurze Begriffe fallen weg
    assert aufrufe["strukturiert"][0]["rolle"] == "schnell"
    treffer = suche.treffer(con, begriffe)
    assert teilaufgabe_id(con, "Überführen Sie die Tabelle") == treffer[0]
    assert suche.treffer(con, []) == []
    assert len(suche.treffer(con, ["Sie"], anzahl=8)) == 8


def test_rag_kontext_mit_seitenkontext(con, ki_mock):
    offen = teilaufgabe_id(con, "Ermitteln Sie")
    text = suche.kontext(con, "Normalform?", (offen,))
    kennungen = re.findall(r'kennung="T(\d+)"', text)
    assert kennungen[0] == str(offen)
    assert str(teilaufgabe_id(con, "Überführen Sie die Tabelle")) in kennungen


def test_rag_ohne_treffer(con, ki_mock):
    _, antworten = ki_mock
    antworten["suche"] = {"begriffe": ["Quantencomputer"]}
    assert "keine passenden Aufgaben" in suche.kontext(con, "Quanten?")


# --- Routen ------------------------------------------------------------------

def test_tipp_streamt_und_speichert(client, bereit, con, ki_mock):
    aufrufe, _ = ki_mock
    tid = teilaufgabe_id(con, "Ermitteln Sie")
    blase = client.post("/sensei/tipp", data={"teilaufgabe": tid}).get_data(as_text=True)
    anfrage_id = re.search(r'sse-connect="/sensei/stream/([0-9a-f]+)"', blase).group(1)
    assert 'sse-swap="delta"' in blase and 'sse-swap="fertig"' in blase and 'sse-close="fertig"' in blase

    antwort = client.get(f"/sensei/stream/{anfrage_id}")
    assert antwort.mimetype == "text/event-stream"
    liste = ereignisse(antwort.get_data(as_text=True))
    # delta kommt höchstens alle 80 ms (hier also einmal), schon als Markdown-HTML, eingebettetes HTML entschärft
    assert [e for e, _ in liste] == ["delta", "fertig"]
    assert liste[0][1].startswith("<p>") and "<b>" not in liste[0][1]
    assert "<b>" not in liste[-1][1] and "Sommer 2023 · Aufgabe 1 a</a>" in liste[-1][1]

    nachrichten = aufrufe["stream"][0]["nachrichten"]
    assert aufrufe["stream"][0]["system"] == prompts.SYSTEM
    assert nachrichten[0]["content"][-1]["text"] == prompts.ANWEISUNG["tipp"]
    gespeichert = con.execute("SELECT rolle, modus, teilaufgabe_id FROM sensei_nachricht ORDER BY id").fetchall()
    assert [tuple(z) for z in gespeichert] == [("user", "tipp", tid), ("assistant", "tipp", tid)]
    # die Anfrage wird nur einmal abgeholt
    assert "abgelaufen" in client.get(f"/sensei/stream/{anfrage_id}").get_data(as_text=True)


def test_variante_gekennzeichnet(client, bereit, con, ki_mock):
    blase = client.post("/sensei/variante", data={"teilaufgabe": 1}).get_data(as_text=True)
    assert "KI-Übung, keine IHK-Aufgabe" in blase


def test_stream_fehler_freundlich(client, bereit, con, ki_mock):
    _, antworten = ki_mock
    antworten["stream"] = ki.KiFehler("weg")
    blase = client.post("/sensei/erklaeren", data={"teilaufgabe": 1}).get_data(as_text=True)
    anfrage_id = re.search(r"/sensei/stream/([0-9a-f]+)", blase).group(1)
    liste = ereignisse(client.get(f"/sensei/stream/{anfrage_id}").get_data(as_text=True))
    assert liste == [("fertig", f'<p class="hinweis hinweis--fehler">{route.NICHT_ERREICHBAR}</p>')]


def test_ungueltige_anfragen(client, bereit):
    assert client.post("/sensei/unbekannt").status_code == 404
    assert client.post("/sensei/tipp", data={"teilaufgabe": 9999}).status_code == 400
    assert client.post("/sensei/thema", data={"thema": 9999}).status_code == 400
    assert "Schreib deine Frage" in client.post("/sensei/chat", data={"frage": " "}).get_data(as_text=True)


def test_pruefen_schlaegt_nur_vor(client, bereit, con, ki_mock):
    aufrufe, _ = ki_mock
    tid = teilaufgabe_id(con, "Ermitteln Sie")
    html = client.post("/sensei/pruefen", data={"teilaufgabe": tid, "antwort": "A-C-E-F"}).get_data(as_text=True)
    assert "Punkte</strong> · Gewusst" in html and '<kbd class="taste">3</kbd>' in html
    assert "Pfad genannt" in html and "Dauer" in html and "Nenne die Dauer." in html
    assert aufrufe["strukturiert"][0]["rolle"] == "stark" and aufrufe["strukturiert"][0]["schema"] is prompts.BEWERTUNG
    assert "<antwort>\nA-C-E-F\n</antwort>" in aufrufe["strukturiert"][0]["text"]
    assert con.execute("SELECT COUNT(*) FROM bewertung").fetchone()[0] == 0  # nie automatisch übernommen
    assert [tuple(z) for z in con.execute("SELECT text, operator FROM luecke")] == [("Dauer", "ermitteln")]
    assert "Deine typischen Lücken" in client.get("/").get_data(as_text=True)
    assert "Schreib zuerst deine Antwort" in client.post("/sensei/pruefen", data={"teilaufgabe": tid}).get_data(as_text=True)


def test_punkte_vorschlag(client, bereit, con, ki_mock):
    _, antworten = ki_mock
    antworten["pruefen"] = {**antworten["pruefen"], "punkte": 9, "max_punkte": 99}
    html = client.post("/sensei/punkte", data={"teilaufgabe": 1, "antwort": "A-C-E-F", "feld_id": "punkte-1"}).get_data(as_text=True)
    assert "6 von 6 Punkten" in html  # gekappt auf die Punkte der Teilaufgabe
    assert 'data-feld="punkte-1"' in html and 'data-wert="6"' in html and "übernehmen" in html
    assert client.post("/sensei/punkte", data={"teilaufgabe": 1, "feld_id": "x\" onclick"}).status_code == 400


def test_chat_mit_rag_und_verlauf(client, bereit, con, ki_mock):
    aufrufe, _ = ki_mock
    gespraech = "a" * 32
    for frage in ("Was kam zu Normalformen?", "Und noch genauer?"):
        blase = client.post("/sensei/chat", data={"frage": frage, "gespraech": gespraech, "teilaufgabe": "", "thema": ""}).get_data(as_text=True)
        assert frage in blase
        client.get("/sensei/stream/" + re.search(r"/sensei/stream/([0-9a-f]+)", blase).group(1)).get_data()
    erste, zweite = (a["nachrichten"] for a in aufrufe["stream"])
    assert len(erste) == 1 and "<aufgabe " in erste[0]["content"][-2]["text"]
    assert erste[0]["content"][-1]["text"].endswith("Was kam zu Normalformen?")
    assert [n["role"] for n in zweite] == ["user", "assistant", "user"]
    assert zweite[0]["content"] == "Was kam zu Normalformen?"
    assert con.execute("SELECT COUNT(*) FROM sensei_nachricht WHERE gespraech = ?", (gespraech,)).fetchone()[0] == 4


# --- Pause und fehlender Schlüssel ---------------------------------------------

def test_pause_waehrend_simulation(client, bereit, con, ki_mock):
    con.execute("INSERT INTO simulation (bereich, dauer_min) VALUES ('Planen eines Softwareproduktes', 90)")
    con.commit()
    assert route.PAUSIERT in client.post("/sensei/tipp", data={"teilaufgabe": 1}).get_data(as_text=True)
    assert route.PAUSIERT in client.post("/sensei/chat", data={"frage": "Hallo?"}).get_data(as_text=True)
    assert 'class="sensei-panel pausiert"' in client.get("/sensei/").get_data(as_text=True)
    assert not ki_mock[0]["stream"] and not ki_mock[0]["strukturiert"]


def test_abgelaufene_simulation_pausiert_nicht(client, bereit, con):
    con.execute("INSERT INTO simulation (bereich, dauer_min, gestartet_am) "
                "VALUES ('Planen eines Softwareproduktes', 90, datetime('now', '-3 hours'))")
    con.commit()
    assert not route.pausiert(con)
    assert 'class="sensei-panel"' in client.get("/sensei/").get_data(as_text=True)


def test_ohne_schluessel_ausgegraut(app, client, con):
    app.config["SENSEI_BEREIT"] = False
    t = prompts.teilaufgabe(con, 1)
    with app.test_request_context("/keiko/"):
        html = render_template_string('{% include "sensei/_keiko.html" %}', teilaufgabe=t)
        vorschlag = render_template_string('{% include "sensei/_punkte_vorschlag.html" %}', teilaufgabe=t, antwort="x", feld_id="p1")
    knoepfe = re.findall(r"<button[^>]*>", html)
    assert len(knoepfe) == 4 and all("disabled" in k for k in knoepfe)
    assert [re.search(r'data-taste="(\w)"', k).group(1) for k in knoepfe] == ["t", "e", "p", "v"]
    assert all('hx-include="#antwort"' in k for k in knoepfe)
    assert "ANTHROPIC_API_KEY" in html and 'href="/einstellungen"' in html
    assert "disabled" in vorschlag
    assert "ANTHROPIC_API_KEY" in client.post("/sensei/tipp", data={"teilaufgabe": 1}).get_data(as_text=True)
    assert 'id="sensei-eingabe"' not in client.get("/sensei/").get_data(as_text=True)


def test_mit_schluessel_aktiv(app, bereit, con):
    t = prompts.teilaufgabe(con, 1)
    with app.test_request_context("/keiko/"):
        html = render_template_string('{% include "sensei/_keiko.html" %}', teilaufgabe=t)
    assert "disabled" not in re.search(r"<button[^>]*>", html).group(0).replace("hx-disabled-elt", "")
    assert 'data-sensei-teilaufgabe="1"' in html


def test_zeichnung_hochladen_und_pruefen(client, bereit, con, ki_mock):
    """Erfundene Zeichnung (1×1-PNG) als data-URL: Sensei bekommt sie als Bild, das starke Modell prüft."""
    import base64
    aufrufe, _ = ki_mock
    tid = teilaufgabe_id(con, "Ermitteln Sie")
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAwS2OUAAAAABJRU5ErkJggg==")
    html = client.post("/sensei/pruefen", data={"teilaufgabe": tid, "automatisch": "1",
                                                "zeichnung": "data:image/png;base64," + base64.b64encode(png).decode()}).get_data(as_text=True)
    aufruf = aufrufe["strukturiert"][-1]
    assert aufruf["rolle"] == "stark" and aufruf["bilder"][0] == ("Zeichnung", png) and "Zeichnung" in aufruf["text"]
    assert "5</span> von 6 Punkten" in html and "Note 2" in html
    # kaputte oder fremde Daten zählen nicht als Zeichnung
    assert "lade eine Zeichnung hoch" in client.post("/sensei/pruefen", data={"teilaufgabe": tid, "zeichnung": "data:text/html;base64,PGI+"}).get_data(as_text=True)


def test_fachgespraech_mit_projekt(client, bereit, con, ki_mock, daten):
    """Erfundenes Projekt als Text: Hochladen, Prüferfragen per Stream mit der Doku im Systemprompt."""
    import io
    aufrufe, _ = ki_mock
    assert "Hochladen" in client.get("/shiken/fachgespraech").get_data(as_text=True)
    assert "Lade zuerst" in client.post("/sensei/fachgespraech", data={}).get_data(as_text=True)
    antwort = client.post("/shiken/fachgespraech/projekt", data={"datei": (io.BytesIO("# Demo-Projekt\nEin erfundenes Ticketsystem.".encode()), "projekt.md")},
                          content_type="multipart/form-data")
    assert antwort.status_code == 302 and (daten / "projekt" / "text.md").exists()
    seite = client.get("/shiken/fachgespraech").get_data(as_text=True)
    assert "projekt.md" in seite and "Fachgespräch starten" in seite
    blase = client.post("/sensei/fachgespraech", data={"gespraech": "a" * 32}).get_data(as_text=True)
    anfrage_id = re.search(r'sse-connect="/sensei/stream/([0-9a-f]+)"', blase).group(1)
    client.get(f"/sensei/stream/{anfrage_id}").get_data()
    assert "erfundenes Ticketsystem" in aufrufe["stream"][-1]["system"]
    assert client.post("/shiken/fachgespraech/projekt", data={"datei": (io.BytesIO(b"x"), "bild.exe")},
                       content_type="multipart/form-data").status_code == 400
