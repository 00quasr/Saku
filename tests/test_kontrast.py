"""Kontrast nach WCAG 2: jede Textfarbe erreicht auf jeder Fläche 4,5 : 1, hell und dunkel (Tokens aus saku.css)."""

import re
from pathlib import Path

import pytest

CSS = (Path(__file__).parents[1] / "saku" / "web" / "static" / "css" / "saku.css").read_text(encoding="utf-8")
TEXT = ("sumi", "sumi-mittel", "shu", "ai", "beni", "yamabuki", "matcha")
FLAECHEN = ("washi", "washi-hell", "flaeche")


def _tokens(selektor: str) -> dict[str, str]:
    block = CSS.split(selektor + " {", 1)[1].split("}", 1)[0]
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", block))


HELL = _tokens(":root")
DUNKEL = {**HELL, **_tokens(".dark")}


def _rgb(farbe: str) -> list[float]:
    return [int(farbe[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def _leuchtdichte(rgb: list[float]) -> float:
    r, g, b = (x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def kontrast(vorne: list[float], hinten: list[float]) -> float:
    hell, dunkel = sorted((_leuchtdichte(vorne), _leuchtdichte(hinten)), reverse=True)
    return (hell + 0.05) / (dunkel + 0.05)


def test_formel_wie_wcag():
    assert round(kontrast([0, 0, 0], [1, 1, 1]), 1) == 21.0
    assert round(kontrast(_rgb("#777777"), _rgb("#FFFFFF")), 2) == 4.48


@pytest.mark.parametrize("schema", [HELL, DUNKEL], ids=["hell", "dunkel"])
@pytest.mark.parametrize("text", TEXT)
def test_textfarben_auf_flaechen(schema, text):
    for flaeche in FLAECHEN:
        assert kontrast(_rgb(schema[text]), _rgb(schema[flaeche])) >= 4.5, (text, flaeche)


def test_reiter_auf_der_flaeche():
    """Basecoat-Reiter: Tusche mit Deckkraft aus saku.css über der Fläche."""
    anteil = int(re.search(r'\[role="tab"\] \{ color: color-mix\(in oklab, var\(--foreground\) (\d+)%', CSS)[1]) / 100
    for schema in (HELL, DUNKEL):
        text, flaeche = _rgb(schema["sumi"]), _rgb(schema["flaeche"])
        gemischt = [anteil * t + (1 - anteil) * f for t, f in zip(text, flaeche)]
        assert kontrast(gemischt, flaeche) >= 4.5
