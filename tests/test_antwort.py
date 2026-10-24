"""Automatisch prüfbare Antworten (erfundene Beispiele)."""

from saku.lernen import antwort

OPT = [{"wert": w, "text": t} for w, t in [("1", "A"), ("2", "B"), ("3", "C"), ("4", "D")]]


def a(art: str, richtig: list[str], **mehr) -> dict:
    return {"art": art, "optionen": OPT, "ziele": [], "richtig": richtig, "einheit": "", "vorlage": ""} | mehr


def test_einfach_und_mehrfach():
    assert antwort.auswerten(a("einfach", ["2"]), {"wahl": ["2"]})[0] == 3
    ergebnis, werte = antwort.auswerten(a("einfach", ["2"]), {"wahl": ["3"]})
    assert ergebnis == 1 and werte == {"1": True, "2": False, "3": False, "4": True}
    assert antwort.auswerten(a("mehrfach", ["1", "3"]), {"wahl": ["1", "3"]})[0] == 3
    assert antwort.auswerten(a("mehrfach", ["1", "3"]), {"wahl": ["1"]})[0] == 2   # einer richtig, keiner falsch
    assert antwort.auswerten(a("mehrfach", ["1", "3"]), {"wahl": ["1", "2"]})[0] == 1


def test_reihenfolge_zuordnung_zahl():
    r = a("reihenfolge", ["3", "1", "2", "4"])
    assert antwort.auswerten(r, {"position": {"3": "1", "1": "2", "2": "3", "4": "4"}})[0] == 3
    assert antwort.auswerten(r, {"position": {"3": "1", "1": "2", "2": "4", "4": "3"}})[0] == 2
    z = a("zuordnung", ["a=2", "b=1"])
    assert antwort.auswerten(z, {"ziel": {"a": "2", "b": "1"}})[0] == 3
    assert antwort.auswerten(z, {"ziel": {"a": "1", "b": "2"}})[0] == 1
    n = a("zahl", ["1234.5"], einheit="€")
    assert antwort.auswerten(n, {"zahl": "1.234,50 €"})[0] == 3
    assert antwort.auswerten(n, {"zahl": "1240"})[0] == 3       # 1 % Toleranz
    assert antwort.auswerten(n, {"zahl": "1300"})[0] == 1
    assert antwort.auswerten(n, {"zahl": "viel"})[0] == 1
    assert antwort.auswerten(a("zahl", ["1.125"]), {"zahl": "1,125"})[0] == 3  # Lösung mit Punkt als Dezimaltrenner


def test_zahl_deutsch_geschrieben():
    for text, wert in [("1,5", 1.5), ("1.024", 1024), ("1 024", 1024), ("1.234,5", 1234.5), ("1.234.567", 1234567),
                       ("0.125", 0.125), ("3.5", 3.5), ("1,234.5", 1234.5), ("  42 MiB", 42), ("ca. 7,5 h", 7.5),
                       ("−3", -3), ("-2,5 °C", -2.5), ("2^16", 65536), ("12.500 €", 12500), ("1\u202f000", 1000)]:
        assert antwort.zahl(text) == wert, text
    assert antwort.zahl("") is None and antwort.zahl("keine") is None and antwort.zahl(None) is None


def test_pruefbar_und_tabelle():
    assert antwort.pruefbar(a("einfach", ["1"])) and not antwort.pruefbar(a("einfach", []))
    assert not antwort.pruefbar(a("frei", ["x"])) and not antwort.pruefbar(None)
    assert antwort.tabelle("| Name | Typ |\n|---|:--:|\n| id |  |\n") == [["Name", "Typ"], ["id", ""]]
    assert antwort.tabelle("| A | B |\n|---|---|\n| x | y |") == [["A", "B"], ["x", "y"], ["", ""], ["", ""]]


def test_operatoren_erkennen():
    from saku.lernen import operatoren
    ops = operatoren.erkennen("Nennen Sie zwei Vorteile und erläutern Sie einen davon. Stellen Sie den Ablauf als Diagramm dar.")
    assert [o["schluessel"] for o in ops] == ["nennen", "erlaeutern", "darstellen"]
    assert operatoren.erkennen("Geben Sie den kritischen Pfad an.")[0]["name"] == "Angeben"
    assert operatoren.erkennen("Ein Text ohne Auftrag.") == [] and operatoren.fuer_sensei(None) == ""
    assert "Stichworte reichen" in operatoren.fuer_sensei("Nennen Sie drei Schutzziele.")
