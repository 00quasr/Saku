"""Eigener Pseudocode: Parser, Grenzen beim Ausführen, „Algorithmus schreiben“, Struktogramm und Routen (nur erfundene Aufgaben)."""

import html
import math
import random
import re

import pytest

from saku.lernen import rechnen
from saku.lernen.rechnen import programmieren, pseudocode
from saku.lernen.rechnen.programmieren import FAMILIEN, Fehler, ersetzen, quelltext, struktogramm

SEEDS = range(150)
HTMX = {"HX-Request": "true"}


def _programme():
    """Alle Programme der Generatoren: Schreibtischtest (auch mit eingebautem Fehler) und die Musterlösungen."""
    for familie in FAMILIEN:
        for seed in range(80):
            p = familie(random.Random(seed))
            yield p["programm"]
            yield from (ersetzen(p["programm"], alt, neu) for alt, neu in p["fehler"].values())
    for seed in range(80):
        yield pseudocode.parsen(rechnen.erzeugen("algorithmus", seed).felder[0].loesung)[0]


def _fehler(code: str, eingaben: dict | None = None) -> str:
    """Die Meldung beim Lesen oder Ausführen."""
    with pytest.raises(Fehler) as f:
        programm, orte = pseudocode.parsen(code)
        pseudocode.laufen(programm, eingaben or {}, orte)
    return str(f.value)


def _ausgabe(code: str, **eingaben) -> str:
    programm, orte = pseudocode.parsen(code)
    return pseudocode.ergebnis(pseudocode.laufen(programm, eingaben, orte), "")


# --- Parser ------------------------------------------------------------------------

def test_rundreise_ueber_alle_generatoren():
    for p in _programme():
        text = quelltext(p)
        gelesen, orte = pseudocode.parsen(text)
        assert gelesen == p, text
        assert sorted(orte.values()) == sorted(set(orte.values()))  # je Anweisung ihre eigene Zeile
        try:
            soll = programmieren.Lauf(p, []).ausgabe
        except Fehler:
            continue
        assert programmieren.Lauf(gelesen, []).ausgabe == soll


def test_varianten_ergeben_denselben_baum():
    kanonisch = """summe ← 0
FÜR i ← 0 BIS länge(zahlen) - 1
    WENN zahlen[i] ≠ 3 UND NICHT (zahlen[i] < 0) DANN
        summe ← summe + zahlen[i]
    SONST
        WENN zahlen[i] ≥ 3 ODER zahlen[i] ≤ -10 DANN
            AUSGABE i, -1
        ENDE WENN
    ENDE WENN
ENDE FÜR
SOLANGE summe > 100
    summe ← summe DIV 2
ENDE SOLANGE
AUSGABE summe, WAHR"""
    variante = """// Summe ohne die Dreien
summe := 0;
fuer i <- 0 bis laenge(zahlen) - 1 tue
   wenn zahlen[i] != 3 und nicht (zahlen[i] < 0)   // Kommentar hinter Code
   dann
      summe <- summe + zahlen[i]
   sonst wenn zahlen[i] >= 3 oder zahlen[i] <= -10 dann
      Ausgabe(i, -1)
   endewenn
ENDE_FÜR

Solange summe > 100
    summe ← summe div 2
Ende
ausgabe: summe, wahr"""
    soll = pseudocode.parsen(kanonisch)[0]
    assert pseudocode.parsen(variante)[0] == soll
    assert pseudocode.parsen(kanonisch.replace("≠", "<>").replace("≥", ">=").replace("≤", "<="))[0] == soll
    assert pseudocode.parsen("FÜR i VON 1 BIS 3\nAUSGABE i\nENDE FÜR")[0] == pseudocode.parsen("FÜR i ← 1 BIS 3\nAUSGABE i\nENDE FÜR")[0]
    assert pseudocode.parsen("WENN a == 1 DANN\nx ← 1\nENDE WENN")[0] == [("wenn", ("=", "a", 1), [("setze", "x", 1)], [])]
    assert quelltext(soll).splitlines()[6] == "            AUSGABE i, -1"  # SONST WENN wird zum WENN im SONST-Zweig
    assert _ausgabe(variante, zahlen=[5, 3, -12, 40]) == "1, -1, 2, -1, 45, WAHR"


def test_vorrang_und_klammern_wie_im_ausdruck():
    for text, wert in [("2 + 3 * 4", "14"), ("(2 + 3) * 4", "20"), ("10 - 4 - 3", "3"), ("10 - (4 - 3)", "9"), ("17 DIV 5 * 5 + 17 MOD 5", "17"),
                       ("-7 DIV 2", "-4"), ("-7 MOD 2", "1"), ("0 - -3", "3"), ("1 < 2 UND 2 < 1 ODER WAHR", "WAHR"),
                       ("NICHT 1 = 1", "FALSCH"), ("NICHT (1 = 2) UND 3 > 2", "WAHR")]:
        programm = pseudocode.parsen(f"x ← {text}")[0]
        assert _ausgabe(f"x ← {text}\nAUSGABE x") == wert, text
        assert pseudocode.parsen(quelltext(programm))[0] == programm, text


@pytest.mark.parametrize("code, meldung", [
    ("x ← 1\nWENN x > 0 DANN\n    x ← 2\n", "Zeile 3: ENDE WENN fehlt (zu WENN in Zeile 2)"),
    ("SOLANGE x > 0\n    WENN x = 3 DANN\n        x ← 0\nENDE SOLANGE", "Zeile 4: ENDE WENN fehlt (zu WENN in Zeile 2), hier steht „ENDE SOLANGE“"),
    ("FÜR i ← 1 BIS 3\n    AUSGABE i\nENDE WENN", "Zeile 3: ENDE FÜR fehlt (zu FÜR in Zeile 1)"),
    ("x ← 1\n\n// nichts\nENDE WENN", "Zeile 4: „ENDE WENN“ ohne passendes WENN"),
    ("x ← 1\nSONST", "Zeile 2: „SONST“ ohne passendes WENN"),
    ("x = 1", "Zeile 1: Zuweisung mit ←"),
    ("x ← 1\ny ← x / 2", "Zeile 2: „/“ gibt es hier nicht: ganzzahlig teilen mit DIV"),
    ('AUSGABE "Summe", 3', "Zeile 1: Texte in Anführungszeichen"),
    ("FÜR i BIS 3\nENDE FÜR", "Zeile 1: FÜR braucht die Form FÜR i ← 1 BIS n."),
    ("x ← [1, 2", "Zeile 1: Im Array fehlt ein Komma oder „]“."),
    ("x ← [1, a]", "Zeile 1: Ein Array hier enthält nur ganze Zahlen"),
    ("ende ← 3", "Zeile 1: „ende“ ist ein Schlüsselwort"),
    ("x ← bis + 1", "Zeile 1: „bis“ ist ein Schlüsselwort"),
    ("AUSGABE", "Zeile 1: Was soll AUSGABE ausgeben?"),
    ("x ←", "Zeile 1: Hier fehlt ein Wert."),
    ("x ← 3 4", "Zeile 1: „4“ verstehe ich hier nicht."),
    ("x ← (1 + 2", "Zeile 1: Am Ende der Klammer fehlt „)“."),
    ("summe + 1", "Zeile 1: Keine Anweisung"),
    ("x ← 1\nDANN", "Zeile 2: Eine Anweisung beginnt nicht mit „DANN“."),
    ("x ← 1\nSONST y ← 2", "Zeile 2: „SONST y ← 2“ ohne passendes WENN"),
    ("x ← 10000000000000", "Zeile 1: Die Zahl ist zu groß"),
    ("x ← 2 $ 3", "Zeile 1: Das Zeichen „$“ verstehe ich nicht."),
    ("// nur ein Kommentar", "Das Programm hat noch keine Anweisung."),
])
def test_fehlermeldungen_mit_zeilennummer(code, meldung):
    assert meldung in _fehler(code)


@pytest.mark.parametrize("code, eingaben, meldung", [
    ("x ← 0\nSOLANGE WAHR\nENDE SOLANGE", {}, "Zeile 2: mehr als 20.000 Schritte, Endlosschleife?"),
    ("i ← 0\nSOLANGE i < 10\n    AUSGABE i\nENDE SOLANGE", {}, "Zeile 3: mehr als 1000 Werte ausgegeben"),
    ("x ← 1\nSOLANGE WAHR\n    x ← x * 10\nENDE SOLANGE", {}, "Zeile 3: x * 10: Zahl zu groß (über 10¹²)"),
    ("FÜR i ← 0 BIS länge(zahlen)\n    AUSGABE zahlen[i]\nENDE FÜR", {"zahlen": [4, 5]}, "Zeile 2: zahlen[i]: Index 2 liegt außerhalb von 0 bis 1"),
    ("AUSGABE zahlen[0]", {"zahlen": []}, "Zeile 1: zahlen[0]: zahlen ist leer"),
    ("AUSGABE zahlen[-1]", {"zahlen": [1, 2]}, "Index -1 liegt außerhalb"),  # kein Lesen von hinten wie in Python
    ("x ← summe + 1", {}, "Zeile 1: summe hat noch keinen Wert"),
    ("x ← 5\nx ← x MOD (x - 5)", {}, "Zeile 2: x MOD (x - 5): Division durch 0"),
    ("x ← zahlen * 2", {"zahlen": [1]}, "mit einem ganzen Array lässt sich nicht rechnen"),
    ("zahlen[0] ← zahlen", {"zahlen": [1]}, "nur ein einzelner Wert"),
    ("x ← länge(n)", {"n": 3}, "n ist kein Array"),
    ("FÜR i ← 1 BIS zahlen\nENDE FÜR", {"zahlen": [1]}, "FÜR zählt nur von einer Zahl bis zu einer Zahl"),
])
def test_grenzen_beim_ausfuehren(code, eingaben, meldung):
    assert meldung in _fehler(code, eingaben)


def test_grenzen_der_eingabe_ohne_absturz():
    assert "zu lang" in _fehler("x ← 1\n" * 1000)
    assert "Zu viele Klammern" in _fehler("x ← " + "(" * 30 + "1" + ")" * 30)
    assert "Zu viele Klammern" in _fehler("x ← " + "NICHT " * 30 + "WAHR")
    assert "Zu tief verschachtelt" in _fehler("WENN WAHR DANN\n" * 25 + "x ← 1\n" + "ENDE WENN\n" * 25)
    assert "Die Zeile ist zu lang" in _fehler("x ← " + " + ".join(["1"] * 150))
    assert "Die Zeile ist zu lang" in _fehler("x ← [" + ", ".join(["1"] * 1001) + "]")  # begrenzt auch Arrays
    # kurz geschlossen: rechts von UND wird nicht mehr gelesen, wenn links schon falsch ist
    assert _ausgabe("i ← 0\nSOLANGE i < länge(zahlen) UND zahlen[i] ≠ 7\n    i ← i + 1\nENDE SOLANGE\nAUSGABE i", zahlen=[1, 2]) == "2"
    eingaben = {"zahlen": [3, 1]}
    _ausgabe("zahlen[0] ← 9\nAUSGABE zahlen", **eingaben)
    assert eingaben == {"zahlen": [3, 1]}  # Lauf kopiert die Eingaben


# --- Algorithmus schreiben ---------------------------------------------------------

def _orakel(a) -> callable:
    """Was das Programm laut Aufgabentext tun soll, unabhängig nachgerechnet; Ergebnis als Liste von Werten."""
    titel, frage = a.titel, a.frage

    def teiler(n):
        return sum(i for i in range(1, n) if n % i == 0)

    def binaer(n):
        return [int(b) for b in reversed(f"{n:b}")]

    def prim(n):
        return n >= 2 and all(n % i for i in range(2, n))

    zaehlen = (lambda z, g: z > g) if "mehr als" in frage else (lambda z, g: z >= g) if "mindestens" in frage else (lambda z, g: z % 2 == 0)
    filtern = (lambda z, g: z < g) if "unter dem Mindestbestand" in frage else (lambda z, g: z >= g)
    return {
        "Summe": lambda e: [sum(e["zahlen"])],
        "Durchschnitt": lambda e: [sum(e["zahlen"]) // len(e["zahlen"]) if e["zahlen"] else 0],
        "Maximum mit Position": lambda e: [max(e["zahlen"]), e["zahlen"].index(max(e["zahlen"]))],
        "Minimum mit Position": lambda e: [min(e["zahlen"]), e["zahlen"].index(min(e["zahlen"]))],
        "Zählen": lambda e: [sum(1 for z in e["zahlen"] if zaehlen(z, e.get("grenze")))],
        "Filtern": lambda e: [z for z in e["zahlen"] if filtern(z, e["grenze"])],
        "Umkehren": lambda e: [e["zahlen"][::-1]],
        "Lineare Suche": lambda e: [e["zahlen"].index(e["gesucht"]) if e["gesucht"] in e["zahlen"] else -1],
        "Fakultät": lambda e: [math.factorial(e["n"])],
        "Primzahltest": lambda e: [prim(e["n"])],
        "Quersumme": lambda e: [sum(map(int, str(e["n"])))],
        "Dezimal → binär": lambda e: binaer(e["n"]),
        "Bubblesort-Durchlauf": lambda e: [_ein_durchlauf(e["zahlen"])],
        "Teilersumme": lambda e: [teiler(e["n"])],
        "Vollkommene Zahl": lambda e: [teiler(e["n"]) == e["n"]],
        "GGT": lambda e: [math.gcd(e["a"], e["b"])],
    }[titel]


def _ein_durchlauf(zahlen: list[int]) -> list[int]:
    z = list(zahlen)
    for i in range(len(z) - 1):
        if z[i] > z[i + 1]:
            z[i], z[i + 1] = z[i + 1], z[i]
    return z


# typische falsche Lösungen: Startwert, Schleife eins zu kurz, Abbruch zu früh, Vergleich an der Grenze
MUTATIONEN = [
    (r"← 0$", "← 1"), (r"^(\w+) ← 1$", r"\1 ← 0"), (r"^(\w+) ← zahlen\[0\]$", r"\1 ← 0"), (r"^i ← 2$", "i ← 1"),
    (r"BIS länge\(zahlen\) - (\d)$", lambda m: f"BIS länge(zahlen) - {int(m[1]) + 1}"),
    (r"BIS länge\(zahlen\) - 1$", "BIS länge(zahlen)"), (r"BIS länge\(zahlen\) - 2$", "BIS länge(zahlen) - 1"),
    (r"BIS länge\(zahlen\) DIV 2 - 1$", "BIS länge(zahlen) DIV 2 - 2"), (r"länge\(zahlen\) - 1 - i\]", "länge(zahlen) - i]"),
    (r"BIS n - 1$", "BIS n"), (r"BIS n$", "BIS n - 1"), (r"^WENN n = 0 DANN\n.*\n.*\n", ""),
    (r"i < länge\(zahlen\)", "i < länge(zahlen) - 1"), (r"i \* i ≤ n", "i * i < n"), (r"SOLANGE n > 0$", "SOLANGE n > 1"),
    (r"SOLANGE b ≠ 0$", "SOLANGE b > 1"), (r"WENN zahlen\[i\] > (grenze|groesste)", r"WENN zahlen[i] ≥ \1"),
    (r"WENN zahlen\[i\] ≥ grenze", "WENN zahlen[i] > grenze"), (r"WENN zahlen\[i\] < (grenze|kleinste)", r"WENN zahlen[i] ≤ \1"),
]


def test_musterloesung_besteht_typische_fehler_fallen_durch():
    erwischt = {}
    for seed in SEEDS:
        a = rechnen.erzeugen("algorithmus", seed)
        loesung, (faelle, ziel) = a.felder[0].loesung, a.testfaelle
        richtig = rechnen.code_vergleich(a, loesung)
        assert richtig["ergebnis"] == 3 and 4 <= len(faelle) <= 6, seed
        orakel = _orakel(a)
        for fall, f in zip(faelle, richtig["faelle"]):
            assert f["erwartet"] == ", ".join(map(pseudocode.wert, orakel(fall))), (seed, a.titel, fall)
        assert any(f["erwartet"] for f in richtig["faelle"])  # leerer Code besteht nie alle
        assert f"`{pseudocode.belegung(faelle[0])}`" in a.frage  # das Beispiel der Frage ist der erste Testfall
        for muster, ersatz in MUTATIONEN:
            falsch = re.sub(muster, ersatz, loesung, count=1, flags=re.M)
            if falsch != loesung:
                assert rechnen.code_vergleich(a, falsch)["ergebnis"] < 3, (seed, a.titel, muster)
                erwischt.setdefault(a.titel, set()).add(muster)
        assert rechnen.code_vergleich(a, "AUSGABE 0")["ergebnis"] < 3
    assert len(erwischt) == 16 and all(len(m) >= (1 if t == "GGT" else 2) for t, m in erwischt.items()), erwischt


def test_ergebnisstufen_und_ein_festes_beispiel():
    a = next(a for _, a in ((s, rechnen.erzeugen("algorithmus", s)) for s in SEEDS) if a.titel == "Summe")
    kurz = a.felder[0].loesung.replace("BIS länge(zahlen) - 1", "BIS länge(zahlen) - 2")
    v = rechnen.code_vergleich(a, kurz)  # leeres Array und ein Element bestehen trotzdem
    assert v["ergebnis"] == 2 and 0 < sum(f["ok"] for f in v["faelle"]) < len(v["faelle"])
    v = rechnen.code_vergleich(a, "summe ← 0\nFÜR i ← 0 BIS länge(zahlen)\n    summe ← summe + zahlen[i]\nENDE FÜR\nAUSGABE summe")
    assert all(f["abbruch"] and "Zeile 3: zahlen[i]: Index" in f["erhalten"] for f in v["faelle"] if f["eingaben"] != "zahlen ← []")
    assert rechnen.code_vergleich(a, "summe ← ")["fehler"] == "Zeile 1: Hier fehlt ein Wert."
    assert not rechnen.pruefen(a, {"code": kurz})["code"] and rechnen.pruefen(a, {"code": a.felder[0].loesung})["code"]
    # anders geschrieben, gleiches Ergebnis: zählt als richtig
    eigene = "s := 0\ni := 0\nsolange i < laenge(zahlen)\n  s := s + zahlen[i]\n  i := i + 1\nende solange\nausgabe s"
    assert rechnen.code_vergleich(a, eigene)["ergebnis"] == 3


# --- Struktogramm ------------------------------------------------------------------

def _anweisungen(block):
    for s in block:
        yield s
        for teil in s[2:] if s[0] in ("wenn", "solange") else s[4:] if s[0] == "fuer" else ():
            yield from _anweisungen(teil)


def test_struktogramm_aller_programme():
    for p in _programme():
        sg = struktogramm(p)
        assert sg.startswith('<div class="struktogramm"') and sg.count("<div") == sg.count("</div>")
        alle = list(_anweisungen(p))
        assert sg.count('class="sg-bedingung"') == sum(s[0] == "wenn" for s in alle)
        assert sg.count('class="sg-kopf"') == sum(s[0] in ("solange", "fuer") for s in alle)
        for s in alle:
            if s[0] == "wenn":  # die Bedingung steht im Kopf der Verzweigung, < und > maskiert
                assert f'<span class="sg-text">{html.escape(programmieren.ausdruck(s[1]), quote=False)}</span>' in sg
            else:
                assert html.escape(programmieren.zeilen([s])[0][0], quote=False) in sg
    assert '<span class="sg-text">a &lt; b</span>' in struktogramm([programmieren.wenn(("<", "a", "b"), [("ausgabe", ["a"])])])


def test_schreibtisch_am_struktogramm():
    gesehen = set()
    for seed in SEEDS:
        a = rechnen.erzeugen("schreibtisch", seed)
        if a.struktogramm:
            gesehen.add(a.titel)
            diagramm = a.titel.split(" am ")[1]
            assert f"als {diagramm}" in a.frage and "```" not in a.frage and "Dasselbe Programm in Pseudocode" in a.rechenweg
    assert gesehen == {f"{t} am {d}" for t in ("Ausgabe", "Endwerte", "Wertetabelle") for d in ("Struktogramm", "Aktivitätsdiagramm")}


# --- Routen ------------------------------------------------------------------------

def _seed(titel: str) -> tuple[int, rechnen.Aufgabe]:
    return next((s, a) for s in SEEDS if (a := rechnen.erzeugen("algorithmus", s)).titel == titel)


def test_algorithmus_anzeigen_ausfuehren(client):
    seed, a = _seed("Bubblesort-Durchlauf")
    html_ = client.get(f"/rechnen/algorithmus?seed={seed}").get_data(as_text=True)
    assert '<textarea class="textarea editor" id="feld-code" name="feld-code"' in html_ and 'oninput="saku.zeilen(this)"' in html_
    assert '<pre class="code-zeilen" aria-hidden="true">1\n</pre>' in html_ and "data-sql-ausfuehren" in html_
    assert 'hx-post="/rechnen/algorithmus/code"' in html_ and "Tabellen ansehen" not in html_ and "Merkblatt: Pseudocode" in html_
    assert "sg-wenn" not in html_  # die Lösung steht erst im Rechenweg

    def ausfuehren(code, **mehr):
        return client.post("/rechnen/algorithmus/code", data={"seed": seed, "feld-code": code} | mehr, headers=HTMX)
    beispiel = a.testfaelle[0][0]
    antwort = ausfuehren("AUSGABE länge(zahlen)").get_data(as_text=True)
    assert f"<code>{html.escape(pseudocode.belegung(beispiel), quote=False)}</code>" in antwort
    assert f"<dd><code>{len(beispiel['zahlen'])}</code></dd>" in antwort and "<dt>zahlen am Ende</dt>" in antwort
    assert "Zeile 2: zahlen[i]: Index" in ausfuehren("i ← 99\nAUSGABE zahlen[i]").get_data(as_text=True)
    assert "Zeile 1: Hier fehlt ein Wert." in ausfuehren("x ←").get_data(as_text=True)
    assert client.post("/rechnen/algorithmus/code", data={"feld-code": "x ← 1"}).status_code == 400
    assert client.post("/rechnen/select/code", data={"seed": 1, "feld-code": "x ← 1"}).status_code == 404  # keine Testfälle
    assert client.post("/rechnen/algorithmus/sql", data={"seed": seed, "feld-sql": "SELECT 1"}).status_code == 404


def test_algorithmus_pruefen_und_aufgeben(client, con):
    seed, a = _seed("Summe")
    loesung = a.felder[0].loesung

    def pruefen(**daten):
        return client.post("/rechnen/algorithmus/pruefen", data={"seed": seed} | daten, headers=HTMX).get_data(as_text=True)
    html_ = pruefen(**{"feld-code": "summe ← 0\nWENN summe > 0 DANN"})  # lässt sich nicht lesen: nichts gespeichert
    assert "Zeile 2: ENDE WENN fehlt" in html_ and "Korrigier den Pseudocode" in html_ and "WENN summe &gt; 0 DANN</textarea>" in html_
    assert '<pre class="code-zeilen" aria-hidden="true">1\n2\n</pre>' in html_
    assert con.execute("SELECT COUNT(*) FROM rechenuebung").fetchone()[0] == 0
    html_ = pruefen(**{"feld-code": loesung})
    assert "Richtig." in html_ and "keiko-urteil--3" in html_ and "rechnen-sql--richtig" in html_ and "code-faelle" not in html_
    assert '<div class="struktogramm"' in html_ and "Formeln: Algorithmus schreiben" in html_
    html_ = pruefen(**{"feld-code": loesung.replace("BIS länge(zahlen) - 1", "BIS länge(zahlen) - 2")})
    assert re.search(r"\d von \d Testfällen bestanden\.", html_) and "keiko-urteil--2" in html_ and "code-fall--falsch" in html_
    assert "<th scope=\"col\">Dein Programm</th>" in html_
    html_ = pruefen(aufgeben="1")
    assert "Hier ist der Rechenweg." in html_ and "Eine mögliche Lösung" in html_ and '<div class="struktogramm"' in html_
    assert [tuple(z) for z in con.execute("SELECT art, richtig, felder_richtig, felder_gesamt FROM rechenuebung ORDER BY id")] == \
        [("algorithmus", 1, 1, 1), ("algorithmus", 0, 0, 1), ("algorithmus", 0, 0, 1)]


def test_struktogramm_auf_karte_und_im_sprint(client):
    seed = next(s for s in SEEDS if rechnen.erzeugen("schreibtisch", s).struktogramm)
    assert '<div class="struktogramm"' in client.get(f"/rechnen/schreibtisch?seed={seed}").get_data(as_text=True)
    sprint = client.get(f"/rechnen/sprint/lauf?a=schreibtisch:{seed}&start=1").get_data(as_text=True)
    assert '<div class="struktogramm"' in sprint
    assert "Nassi-Shneiderman" in client.get("/rechnen/formeln").get_data(as_text=True)
    assert [a.slug for a in rechnen.passende(["Struktogramme lesen und erstellen"])] == ["schreibtisch", "algorithmus"]
