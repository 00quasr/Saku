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


# --- Zustandsdiagramm ------------------------------------------------------------------------

def _automat(svg: ET.Element) -> tuple[str, list[tuple]]:
    """Startzustand und Übergänge aus der Textfassung des Diagramms (aria-label)."""
    text = svg.get("aria-label", "")
    return re.search(r"Startzustand „(.+?)“", text)[1], re.findall(
        r"von „(.+?)“ nach „(.+?)“ bei (\S+)(?: \[\w+ ([<=]) (\d+)\])?(?: / \w+ ← ([^;]+))?(?:;|$)", text)


def _simulieren(start: str, uebergaenge: list[tuple], folge: list[str]) -> tuple[str, int]:
    zustand, n = start, 0
    for e in folge:
        for von, nach, ereignis, op, zahl, wirkung in uebergaenge:
            if von == zustand and ereignis == e and (not op or (n < int(zahl) if op == "<" else n == int(zahl))):
                zustand, n = nach, n + 1 if wirkung.endswith("+ 1") else 0 if wirkung == "0" else n
                break
    return zustand, n


def test_zustandsdiagramm_selbst_nachgespielt():
    titel = set()
    for seed, a in _alle("zustand"):
        svg = svg_pruefen(a.struktogramm)
        start, uebergaenge = _automat(svg)
        zustaende = {u[0] for u in uebergaenge} | {u[1] for u in uebergaenge}
        assert zustaende <= set(_texte(svg)) and {u[2] for u in uebergaenge} <= {t.split()[0] for t in _texte(svg)}
        # je Zustand und Ereignis schaltet höchstens ein Übergang, für jeden Zählerstand
        for (von, e), n in itertools.product({(u[0], u[2]) for u in uebergaenge}, range(8)):
            assert sum(1 for u in uebergaenge if (u[0], u[2]) == (von, e) and (not u[3] or (n < int(u[4]) if u[3] == "<" else n == int(u[4])))) <= 1
        titel.add(a.titel)
        felder = {f.name: f for f in a.felder}
        if a.titel == "Ereignisfolge nachspielen":
            folge = re.search(r"Ereignisfolge ab dem Startzustand: `(.*?)`", a.frage)[1].split(", ")
            zustand, n = _simulieren(start, uebergaenge, folge)
            assert a.loesung["zustand"] == zustand and a.loesung.get("zaehler", n) == n, seed
            falsch = next(z for z in felder["zustand"].optionen if z != zustand)
            assert not rechnen.pruefen(a, {"zustand": falsch, "zaehler": str(n)})["zustand"]
            if "zaehler" in felder:
                assert not rechnen.pruefen(a, {"zaehler": str(n + 1)})["zaehler"]
        else:
            ziel = re.search(r"in den Zustand \*\*„(.+?)“\*\*", a.frage)[1]
            treffer = [o for o in felder["folge"].optionen if _simulieren(start, uebergaenge, o.split(", "))[0] == ziel]
            assert treffer == [a.loesung["folge"]] and len(felder["folge"].optionen) >= 3, seed
    assert titel == {"Ereignisfolge nachspielen", "Ereignisfolge finden"}


def test_zustandsdiagramm_alle_automaten():
    from saku.lernen.rechnen import uml
    namen = set()
    for automat, seed in itertools.product(uml.AUTOMATEN, range(4)):
        a = automat(random.Random(seed))
        svg_pruefen(uml.zustandsdiagramm(a))
        namen.add(a["name"])
        # Selbstübergänge nur oben oder unten im Raster, alle anderen in derselben Zeile oder Spalte
        zeilen = max(r for r, _ in a["zustaende"].values())
        for von, _, _, nach, _ in a["uebergaenge"]:
            (r1, s1), (r2, s2) = a["zustaende"][von], a["zustaende"][nach]
            assert r1 in (0, zeilen) if von == nach else (r1 == r2) != (s1 == s2)
    assert len(namen) == len(uml.AUTOMATEN)
    # verfallende Ereignisse und Zähler: dreimal falsch sperrt, danach verfällt das richtige Passwort
    konto = uml._konto(random.Random(0))
    n = int(re.search(r"nach (\d) falschen", konto["text"])[1])
    spur = uml.nachspielen(konto, ["passwortFalsch"] * n + ["passwortRichtig"])
    assert [s[3] for s in spur] == ["Abgemeldet"] * (n - 1) + ["Gesperrt", "Gesperrt"] and spur[-1][2] is None


# --- Klassendiagramm ---------------------------------------------------------------------------

def _klassenmodell(svg: ET.Element) -> tuple[dict, dict, list]:
    """Klassen (Art, Attribute, Methoden), Oberklasse je Unterklasse und Verbindungen (Art, a, Multiplizität a, b, Multiplizität b)
    aus der Textfassung."""
    klassen_teil, bez_teil = svg.get("aria-label", "").split(" Beziehungen: ")
    klassen = {name: (art, [] if attr == "keine" else attr.split("; "), meth.split("; ")) for art, name, attr, meth in
               re.findall(r"(Klasse|Abstrakte Klasse|Interface) (\w+)\. Attribute: (.*?)\. Methoden: (.*?)\.", klassen_teil)}
    oben, verbindungen = {}, []
    ende = r"(\w+) \(([\d.*]+)(?:, Rolle \w+)?\)"
    for teil in bez_teil.removesuffix(".").split("; "):
        if m := re.fullmatch(r"(\w+) (?:erbt von|realisiert) (\w+)", teil):
            oben[m[1]] = m[2]
        elif m := re.fullmatch(rf"Assoziation zwischen {ende} und {ende}", teil):
            verbindungen.append(("Assoziation", *m.groups()))
        else:
            m = re.fullmatch(rf"(Aggregation|Komposition): Ganzes {ende}, Teil {ende}", teil)
            verbindungen.append(m.groups())
    return klassen, oben, verbindungen


def _grenzen(m: str) -> tuple[int, int | None]:
    """Multiplizität, unabhängig gelesen: 1, 0..1, 0..*, 1..*, 0..5."""
    teile = m.split("..")
    return int(teile[0]), (None if teile[-1] == "*" else int(teile[-1]))


def _alle_attribute(klassen: dict, oben: dict, k: str) -> list[str]:
    return klassen[k][1] + (_alle_attribute(klassen, oben, oben[k]) if k in oben else [])


def _alle_methoden(klassen: dict, oben: dict, k: str) -> set[str]:
    eigene = {re.sub(r"^\+ (\w+)\(.*", r"\1", m) for m in klassen[k][2]}
    return eigene | (_alle_methoden(klassen, oben, oben[k]) if k in oben else set())


def test_klassendiagramm_selbst_ausgewertet():
    titel = set()
    for seed, a in _alle("klassen"):
        svg = svg_pruefen(a.struktogramm)
        klassen, oben, verbindungen = _klassenmodell(svg)
        texte = set(_texte(svg))
        assert 3 <= len(klassen) <= 5 and set(klassen) <= texte, seed
        assert all(x in texte for _, attr, meth in klassen.values() for x in attr + [m.removesuffix(" (abstrakt)") for m in meth])
        l, felder = a.loesung, {f.name: f for f in a.felder}
        titel.add(a.titel)
        if a.titel == "Multiplizitäten":
            x, y = re.search(r"zwischen \*\*(\w+)\*\* und \*\*(\w+)\*\*", a.frage).groups()
            _, k1, m1, k2, m2 = next(v for v in verbindungen if {v[1], v[3]} == {x, y})
            am = {k1: _grenzen(m1), k2: _grenzen(m2)}  # die Multiplizität am Ende der gezählten Klasse
            erwartet = {"ab_min": am[y][0], "ab_max": am[y][1], "ba_min": am[x][0], "ba_max": am[x][1]}
            assert {k: (None if v == "beliebig viele" else v) for k, v in l.items()} == erwartet, seed
            if am[x] != am[y]:  # das nahe Ende abgelesen: falsch
                nah = {"ab_min": am[x][0], "ab_max": am[x][1], "ba_min": am[y][0], "ba_max": am[y][1]}
                eingaben = {k: "beliebig viele" if v is None else str(v) for k, v in nah.items()}
                assert not all(rechnen.pruefen(a, eingaben).values()), seed
        elif a.titel == "Beziehungen":
            for f in a.felder:
                x, y = f.label.split(" – ")
                if oben.get(x) == y:
                    soll = "Realisierung" if klassen[y][0] == "Interface" else "Generalisierung"
                else:
                    soll = next(v[0] for v in verbindungen if {v[1], v[3]} == {x, y})
                assert f.loesung.startswith(soll), (seed, f.label)
        elif a.titel == "Vererbung":
            u = re.search(r"Objekt der Klasse \*\*(\w+)\*\*", a.frage)[1]
            assert l["attribute"] == len(_alle_attribute(klassen, oben, u)) and l["methoden"] == len(_alle_methoden(klassen, oben, u)), seed
            assert [k for k, v in klassen.items() if v[0] != "Klasse"] == [l["abstrakt"]]
            assert not rechnen.pruefen(a, {"attribute": str(len(klassen[u][1]))})["attribute"] or not klassen[oben[u]][1]
        elif a.titel == "Sichtbarkeit":
            u = re.search(r"der Klasse \*\*(\w+)\*\*", a.frage)[1]
            sichtbar = [x.split()[1].rstrip(":") for x in klassen[oben[u]][1] if x[0] in "+#"]  # anderes Paket: ~ zählt nicht
            assert sichtbar == [l["zugriff"]], seed
            name = felder["sicht"].label.removeprefix("Sichtbarkeit von ")
            zeichen = next(x[0] for x in klassen[oben[u]][1] if x.split()[1] == f"{name}:")
            assert l["sicht"] == {"+": "public", "-": "private", "#": "protected", "~": "package"}[zeichen]
        else:
            g, t = re.search(r"Zwischen \*\*(\w+)\*\* und \*\*(\w+)\*\*", a.frage).groups()
            art, ganzes, mg, teil, _ = next(v for v in verbindungen if (v[1], v[3]) == (g, t))
            unten, hoch = _grenzen(mg)
            assert l == {"loeschen": "werden mitgelöscht" if art == "Komposition" else "bleiben bestehen",
                         "mehrere": "Ja" if hoch is None or hoch > 1 else "Nein", "ohne": "Ja" if unten == 0 else "Nein"}, seed
    assert titel == {"Multiplizitäten", "Beziehungen", "Vererbung", "Sichtbarkeit", "Ganzes und Teil"}


def test_klassendiagramm_alle_modelle_und_beliebig_viele():
    from saku.lernen.rechnen import uml
    for seed in range(300):
        svg_pruefen(uml.klassendiagramm(uml._modell(random.Random(seed))))
    feld = uml._vielheit_feld("x", "höchstens", None)
    assert all(rechnen.stimmt(feld, t) for t in ["beliebig viele", "*", "n", "unbegrenzt", "Beliebig"]) and not rechnen.stimmt(feld, "1")
    assert [uml._vielheit(m) for m in ("1", "0..1", "*", "0..*", "1..*", "0..5")] == [(1, 1), (0, 1), (0, None), (0, None), (1, None), (0, 5)]
