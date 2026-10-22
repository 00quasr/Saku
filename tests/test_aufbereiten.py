"""Aufbereiten: Antwort von Claude speichern, Abbildungen schneiden, Bilder an Claude Code geben (alles erfunden)."""

import json
import subprocess

import pymupdf

from saku.pipeline import aufbereiten
from saku.sensei import client as ki


def _antwort(nummer: int, kennung: str, **teil) -> dict:
    return {"ausgangssituation": "", "abbildungen": teil.pop("abbildungen", []), "aufgaben": [{
        "nummer": nummer, "einleitung": "Die Demo GmbH plant ein **Lager**.", "teilaufgaben": [{
            "kennung": kennung, "inhalt": "Welche Aussage stimmt?\n\n![Lagerplan](abb:1)",
            "antwort": {"art": "einfach", "optionen": [{"wert": "1", "text": "A"}, {"wert": "2", "text": "B"}], "ziele": [],
                        "richtig": ["2"], "einheit": "", "vorlage": ""},
            "loesung": "Richtig ist **2**.", "begriffe": ["Lagerhaltung", "lagerhaltung", "x"], **teil}]}]}


def test_speichern_mit_abbildung_und_begriffen(con, daten):
    a = con.execute("SELECT a.*, t.kennung, t.bilder FROM aufgabe a JOIN teilaufgabe t ON t.aufgabe_id = a.id LIMIT 1").fetchone()
    bild = daten / json.loads(a["bilder"])[0]
    antwort = _antwort(a["nummer"], a["kennung"] + ")", abbildungen=[{"nr": 1, "bild": "B", "beschreibung": "Lagerplan",
                                                                        "box": [0.1, 0.1, 0.9, 0.8]}])
    assert aufbereiten.speichern(con, daten, [a], [("B", bild)], antwort) == 1

    t = con.execute("SELECT * FROM teilaufgabe WHERE aufgabe_id = ? AND kennung = ?", (a["id"], a["kennung"])).fetchone()
    url = t["inhalt"].split("](")[1].rstrip(")")
    assert url.startswith("/bild/aufgaben/") and url.endswith("-abb1.png") and (daten / url.removeprefix("/bild/")).exists()
    assert t["text"] == "Welche Aussage stimmt?\n\nLagerplan"  # Klartext für Suche
    assert json.loads(t["antwort"])["richtig"] == ["2"] and t["loesung_inhalt"] == "Richtig ist **2**."
    assert con.execute("SELECT einleitung_inhalt FROM aufgabe WHERE id = ?", (a["id"],)).fetchone()[0].startswith("Die Demo")
    # „Lagerhaltung“ doppelt in anderer Schreibweise, „x“ zu kurz: ein Begriff
    assert [z[0] for z in con.execute("SELECT b.name FROM begriff b JOIN teilaufgabe_begriff tb ON tb.begriff_id = b.id "
                                      "WHERE tb.teilaufgabe_id = ?", (t["id"],))] == ["Lagerhaltung"]


def test_unbekannte_abbildung_wird_text(con, daten):
    a = con.execute("SELECT a.*, t.kennung FROM aufgabe a JOIN teilaufgabe t ON t.aufgabe_id = a.id LIMIT 1").fetchone()
    aufbereiten.speichern(con, daten, [a], [], _antwort(a["nummer"], a["kennung"]))
    inhalt = con.execute("SELECT inhalt FROM teilaufgabe WHERE aufgabe_id = ? AND kennung = ?", (a["id"], a["kennung"])).fetchone()[0]
    assert inhalt.endswith("Lagerplan") and "abb:" not in inhalt


def test_abbildung_aus_text_pdf_als_svg(con, daten):
    pdf = daten / "pdfs" / "probe.pdf"
    pdf.parent.mkdir(exist_ok=True)
    doc = pymupdf.open()
    seite = doc.new_page()
    seite.insert_text((100, 150), "Erfundene Abbildung")
    seite.draw_rect(pymupdf.Rect(90, 120, 300, 200))
    doc.save(pdf)
    ordner = daten / "aufgaben" / "abcdef123456"
    ordner.mkdir(parents=True)
    pymupdf.open(pdf)[0].get_pixmap(clip=pymupdf.Rect(50, 100, 400, 300)).save(ordner / "1a-1.png")
    (ordner / "ausschnitte.json").write_text(json.dumps({"1a-1.png": [0, 50, 100, 400, 300]}))
    con.execute("INSERT INTO dokument (dateiname, sha256, seiten, art, hat_textebene) VALUES ('probe.pdf', 'abcdef123456ff', 1, 'aufgaben', 1)")

    rel = aufbereiten.abbildung(con, daten, ordner / "1a-1.png", [0, 0, 0.8, 0.6], "1a-1-abb1")
    svg = (daten / rel).read_text()
    assert rel.endswith(".svg") and svg.startswith("<svg") and 'viewBox="0 0 280 120"' in svg
    assert aufbereiten.abbildung(con, daten, ordner / "1a-1.png", [0.5, 0.5, 0.51, 0.51], "zu-klein") is None


def test_claude_code_bekommt_bilder(con, daten, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    aufrufe = []

    def lauf(befehl, **kw):
        assert "ANTHROPIC_API_KEY" not in kw["env"]  # sonst zahlt die API statt das Claude-Abo
        aufrufe.append((befehl, kw["input"]))
        return subprocess.CompletedProcess(befehl, 0, stdout=json.dumps(
            {"is_error": False, "structured_output": {"x": 1}, "usage": {}}), stderr="")

    monkeypatch.setattr(subprocess, "run", lauf)
    bild = next((daten / "aufgaben").rglob("*.png"))
    schema = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"], "additionalProperties": False}
    assert ki.strukturiert(con, "test", "stark", "sys", "frage", schema, ki="claude-code", bilder=[("A1", bild)]) == {"x": 1}
    befehl, eingabe = aufrufe[0]
    assert befehl[befehl.index("--tools") + 1] == "Read" and befehl[befehl.index("--add-dir") + 1] == str(bild.parent)
    assert f"- A1: {bild}" in eingabe
    # anderes Bild, andere Anfrage: kein Cache-Treffer
    bild.write_bytes(bild.read_bytes() + b"\0")
    ki.strukturiert(con, "test", "stark", "sys", "frage", schema, ki="claude-code", bilder=[("A1", bild)])
    assert len(aufrufe) == 2


def test_begriff_mit_gleichem_slug(con):
    a, b = aufbereiten.begriff_id(con, "Client-Server"), aufbereiten.begriff_id(con, "Client Server")
    assert a != b and aufbereiten.begriff_id(con, "client-server") == a
    assert [z[0] for z in con.execute("SELECT slug FROM begriff ORDER BY id")] == ["client-server", "client-server-2"]


def test_vektoren_ohne_modell_und_verschmelzen(con):
    """Rangfusion bevorzugt, was in beiden Listen vorn liegt; ohne gespeicherte Vektoren gibt die Suche nichts."""
    import numpy as np
    from saku.pipeline import vektoren as schritt
    from saku.sensei import vektoren
    assert vektoren.verschmelzen([1, 2, 3], [3, 1, 4])[:2] == [1, 3]
    assert vektoren.suchen(con, "teilaufgabe", "Netzplan") == []
    assert vektoren.klartext("**fett** ![Plan](/bild/x.png) | a |") == "fett Plan a"
    # zwei fast gleiche Aufgaben aus verschiedenen Prüfungen sind ähnlich, die aus derselben nicht
    m = np.array([[1, 0], [0.99, 0.14], [1, 0.01]], dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    assert {(i, j) for i, j, _ in schritt.aehnlichkeiten(m, [1, 2, 1])} == {(0, 1), (1, 0), (1, 2), (2, 1)}


def test_wissen_schreibt_nur_fehlendes(con, daten, monkeypatch):
    import re
    from saku.pipeline import wissen
    b_id = con.execute("INSERT INTO begriff (name, slug) VALUES ('Primärschlüssel', 'primaerschluessel')").lastrowid
    con.commit()
    aufrufe = []

    def strukturiert(c, zweck, rolle, system, text, schema, **kw):
        aufrufe.append(rolle)
        if schema is wissen.SCHEMA_BEGRIFFE:
            return {"begriffe": [{"id": b_id, "erklaerung": "Eindeutige Kennung eines Datensatzes."}, {"id": 999, "erklaerung": "fremd"}]}
        unter = [int(i) for i in re.findall(r"## Unterthema (\d+):", text)]
        return {"thema": "Übersicht", "unterthemen": [{"id": i, "notiz": f"Notiz {i}"} for i in unter] + [{"id": 1, "notiz": "fremd"}]}

    monkeypatch.setattr(wissen.client, "strukturiert", strukturiert)
    wissen.ausfuehren(con, daten, False, "claude-code")
    assert con.execute("SELECT erklaerung FROM begriff WHERE id = ?", (b_id,)).fetchone()[0] == "Eindeutige Kennung eines Datensatzes."
    assert con.execute("SELECT COUNT(*) FROM thema WHERE ebene > 1 AND beschreibung IS NULL").fetchone()[0] == 0
    assert con.execute("SELECT beschreibung FROM thema WHERE id = 1").fetchone()[0] is None  # Bereich bleibt leer
    assert "[T" in wissen.themen_auftrag(con, con.execute("SELECT * FROM thema WHERE ebene = 2 LIMIT 1").fetchone())
    anzahl = len(aufrufe)
    wissen.ausfuehren(con, daten, False, "claude-code")
    assert len(aufrufe) == anzahl  # zweiter Lauf: nichts mehr offen
