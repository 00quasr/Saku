"""Diagramme als SVG und die Gruppe UML: Geometrie, Texte, Lösungen unabhängig nachgerechnet (nur erfundene Modelle)."""

import itertools
import random
import re
import xml.etree.ElementTree as ET

from saku.lernen import rechnen

SEEDS = range(150)
ZEICHEN = 7.2  # 12 px dicktengleich, wie svg.py


def _alle(art: str, titel: str | None = None):
    for seed in SEEDS:
        a = rechnen.erzeugen(art, seed)
        if titel is None or a.titel.startswith(titel):
            yield seed, a


# --- Geometrie, unabhängig von svg.py aus dem fertigen SVG gelesen ---------------------------

def _zahlen(text: str) -> list[float]:
    return [float(z) for z in re.findall(r"-?[\d.]+", text)]


def _form(e) -> tuple[str, tuple] | None:
    """(Art, Rahmen) einer Fläche: Kasten, Ellipse, Raute oder Kreis."""
    if "uml-kasten" not in e.get("class", "").split():
        return None
    if e.tag == "rect":
        x, y, b, h = (float(e.get(k)) for k in ("x", "y", "width", "height"))
        return "rect", (x, y, x + b, y + h)
    if e.tag in ("ellipse", "circle"):
        cx, cy = float(e.get("cx")), float(e.get("cy"))
        rx, ry = (float(e.get("r")),) * 2 if e.tag == "circle" else (float(e.get("rx")), float(e.get("ry")))
        return "ellipse", (cx - rx, cy - ry, cx + rx, cy + ry)
    z = _zahlen(e.get("points", ""))
    xs, ys = z[::2], z[1::2]
    return "raute", (min(xs), min(ys), max(xs), max(ys))


def _innen(form: tuple[str, tuple], x: float, y: float) -> bool:
    """Liegt der Punkt deutlich im Inneren der Fläche (der Rand zählt nicht)?"""
    art, (x0, y0, x1, y1) = form
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    if art == "rect":
        return x0 + 1.5 < x < x1 - 1.5 and y0 + 1.5 < y < y1 - 1.5
    if art == "ellipse":
        return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 < 0.92
    return abs(x - cx) / rx + abs(y - cy) / ry < 0.9


def _textrahmen(e) -> tuple:
    x, y, b = float(e.get("x")), float(e.get("y")), len(e.text or "") * ZEICHEN
    links = {"start": x, "middle": x - b / 2, "end": x - b}[e.get("text-anchor", "start")]
    return links, y - 10, links + b, y + 3


def _ueber(a, b, luft: float = 0) -> bool:
    return a[0] < b[2] - luft and b[0] < a[2] - luft and a[1] < b[3] - luft and b[1] < a[3] - luft


def _enthaelt(aussen, innen) -> bool:
    return aussen[0] <= innen[0] + 0.5 and aussen[1] <= innen[1] + 0.5 and innen[2] <= aussen[2] + 0.5 and innen[3] <= aussen[3] + 0.5


def svg_pruefen(bild) -> ET.Element:
    """Gültiges XML mit role="img" und Beschreibung, keine festen Farben; Flächen überlappen nicht (außer dem Systemrahmen, der
    andere umschließt), Text steht ganz in einer Fläche oder frei, Beschriftungen überdecken sich nicht, Linien laufen durch keine
    Fläche und keinen Text."""
    svg = ET.fromstring(str(bild))
    assert svg.tag == "svg" and svg.get("role") == "img" and len(svg.get("aria-label", "")) > 20
    for e in svg.iter():
        assert not {"fill", "stroke", "style", "color"} & set(e.attrib), (e.tag, e.attrib)
    formen = [f for e in svg.iter() if (f := _form(e))]
    rahmen = [f for e in svg.iter() if (f := _form(e)) and "uml-rahmen" in e.get("class", "")]
    flaechen = [f for f in formen if f not in rahmen]
    for a, b in itertools.combinations(flaechen, 2):
        assert not _ueber(a[1], b[1], 0.5), ("Flächen überlappen", a, b)
    for r in rahmen:
        assert all(_enthaelt(r[1], f[1]) or not _ueber(r[1], f[1]) for f in flaechen)
    texte = [(e.text, _textrahmen(e)) for e in svg.iter("text")]
    freie = []
    for text, r in texte:
        drin = [f for f in flaechen if _enthaelt(f[1], r)]
        assert drin or not any(_ueber(r, f[1], 0.5) for f in flaechen), ("Text auf einer Fläche", text)
        if not drin:
            freie.append((text, r))
    for (t1, r1), (t2, r2) in itertools.combinations(texte, 2):
        assert not _ueber(r1, r2, 0.5), ("Texte überdecken sich", t1, t2)
    for e in svg.iter("polyline"):
        if "uml-linie" not in e.get("class", ""):
            continue
        z = _zahlen(e.get("points", ""))
        for (x0, y0), (x1, y1) in itertools.pairwise(zip(z[::2], z[1::2])):
            for i in range(41):
                x, y = x0 + (x1 - x0) * i / 40, y0 + (y1 - y0) * i / 40
                assert not any(_innen(f, x, y) for f in flaechen), ("Linie durch eine Fläche", (x0, y0, x1, y1))
                assert not any(r[0] + 1 < x < r[2] - 1 and r[1] + 1 < y < r[3] - 1 for _, r in freie), ("Linie durch Text", (x, y))
    return svg


def _texte(svg: ET.Element) -> list[str]:
    return [e.text or "" for e in svg.iter("text")]


# --- Aktivitätsdiagramm (Schreibtischtest) ---------------------------------------------------

def test_aktivitaetsdiagramm_zeigt_das_programm():
    from saku.lernen.rechnen import programmieren as p
    gesehen = 0
    for seed, a in _alle("schreibtisch"):
        if not a.titel.endswith("am Aktivitätsdiagramm"):
            continue
        gesehen += 1
        texte = _texte(svg_pruefen(a.struktogramm))
        assert "Aktivitätsdiagramm" in a.frage and "```" in a.rechenweg and not a.titel.startswith("Fehlersuche")
        code = re.search(r"```\n(.*?)```", a.rechenweg, re.S)[1]
        for zeile in code.splitlines():
            befehl = re.sub(r"^\s*\d+  \s*", "", zeile)
            if m := re.fullmatch(r"(?:WENN (.*) DANN|SOLANGE (.*))", befehl):
                assert f"[{m[1] or m[2]}]" in texte, (seed, befehl)
            elif m := re.fullmatch(r"FÜR (\w+) ← (.*) BIS (.*)", befehl):  # aufgelöst: Startwert, Bedingung, Erhöhen
                assert {f"{m[1]} ← {m[2]}", f"[{m[1]} ≤ {m[3]}]", f"{m[1]} ← {m[1]} + 1"} <= set(texte), (seed, befehl)
            elif not befehl.startswith(("ENDE", "SONST")):
                assert befehl in texte, (seed, befehl)
    assert gesehen > 15
    # jede Familie einmal, auch ohne Aufgabe drumherum
    for familie in p.FAMILIEN:
        for seed in range(5):
            svg_pruefen(p.aktivitaetsdiagramm(familie(random.Random(seed))["programm"]))


def test_aktivitaetsdiagramm_wertetabelle_nie_mit_zaehlschleife():
    """Im Diagramm ist i am Ende eines Durchlaufs schon erhöht, in der Wertetabelle (wie im Pseudocode) noch nicht."""
    for _, a in _alle("schreibtisch", "Wertetabelle am Aktivitätsdiagramm"):
        assert "FÜR" not in a.rechenweg


def test_verneinte_bedingung():
    from saku.lernen.rechnen.programmieren import ausdruck, nicht
    assert [ausdruck(nicht(b)) for b in [("<", "i", 5), ("=", ("MOD", "i", 2), 0), ("NICHT", "fertig"), ("UND", "a", "b")]] == \
        ["i ≥ 5", "i MOD 2 ≠ 0", "fertig", "NICHT (a UND b)"]


def test_svg_pruefen_findet_fehler():
    """Die Prüfung selbst: überlappende Kästen, Linie durch einen Kasten und feste Farben fallen auf."""
    import pytest
    from saku.lernen.rechnen.svg import Bild

    def bild(*schritte):
        b = Bild()
        for s in schritte:
            s(b)
        return b.svg("x", "Ein Testbild mit genug Beschreibung")
    svg_pruefen(bild(lambda b: b.kasten(0, 0, 50, 30), lambda b: b.kasten(80, 0, 50, 30), lambda b: b.pfeil([(50, 15), (80, 15)])))
    for kaputt in ((lambda b: b.kasten(0, 0, 50, 30), lambda b: b.kasten(40, 10, 50, 30)),
                   (lambda b: b.kasten(0, 0, 50, 30), lambda b: b.linie([(-10, 15), (60, 15)])),
                   (lambda b: b.kasten(0, 0, 50, 30), lambda b: b.text(0, 50, "lang genug"), lambda b: b.text(10, 52, "darüber"))):
        with pytest.raises(AssertionError):
            svg_pruefen(bild(*kaputt))
    with pytest.raises(AssertionError):
        svg_pruefen(str(bild(lambda b: b.kasten(0, 0, 50, 30))).replace('class="uml-kasten"', 'fill="#fff" class="uml-kasten"'))
