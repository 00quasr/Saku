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
